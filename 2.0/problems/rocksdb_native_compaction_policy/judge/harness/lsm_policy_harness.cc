// Runs identical deterministic workloads against vanilla and candidate
// RocksDB builds.

#include <rocksdb/cache.h>
#include <rocksdb/db.h>
#include <rocksdb/listener.h>
#include <rocksdb/metadata.h>
#include <rocksdb/options.h>
#include <rocksdb/statistics.h>
#include <rocksdb/table.h>
#include <rocksdb/table_properties.h>
#include <rocksdb/version.h>

#include <algorithm>
#include <atomic>
#include <cctype>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <utility>
#include <vector>

namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;

// Helpers

static inline uint64_t SplitMix64(uint64_t& x) {
  uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
  z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
  z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
  return z ^ (z >> 31);
}

static inline uint64_t Rng(uint64_t seed, uint32_t phase, uint64_t op_index,
                           uint64_t stream) {
  uint64_t x = seed ^ (0x9e3779b97f4a7c15ULL * (phase + 1));
  x ^= op_index * 0xbf58476d1ce4e5b9ULL;
  x ^= stream * 0x94d049bb133111ebULL;
  return SplitMix64(x);
}

// 128-bit value hash (two independent FNV-1a streams).
static inline std::pair<uint64_t, uint64_t> Hash128(const char* p, size_t n) {
  uint64_t h1 = 1469598103934665603ULL;
  uint64_t h2 = 1099511628211ULL ^ 0xff51afd7ed558ccdULL;
  for (size_t i = 0; i < n; ++i) {
    unsigned char c = static_cast<unsigned char>(p[i]);
    h1 = (h1 ^ c) * 1099511628211ULL;
    h2 = (h2 ^ c) * 0x100000001b3ULL;
    h2 = (h2 << 7) | (h2 >> 57);
  }
  return {h1, h2};
}
static inline std::pair<uint64_t, uint64_t> Hash128(const std::string& s) {
  return Hash128(s.data(), s.size());
}

// Per-key token folded into an order-independent XOR aggregate.
static inline uint64_t KeyToken(uint64_t id, uint32_t size, uint64_t h1,
                                uint64_t h2) {
  uint64_t x = id * 0x9e3779b97f4a7c15ULL;
  x ^= (uint64_t(size) + 0x100) * 0xbf58476d1ce4e5b9ULL;
  x ^= h1;
  x ^= (h2 << 1) | (h2 >> 63);
  return SplitMix64(x);
}

static inline std::string MakeKey(uint64_t key_id, uint64_t seed) {
  std::string k(16, '\0');
  uint64_t salt = key_id ^ (seed * 0x9e3779b97f4a7c15ULL);
  for (int i = 0; i < 8; ++i) k[i] = char((key_id >> (56 - 8 * i)) & 0xff);
  for (int i = 0; i < 8; ++i) k[8 + i] = char((salt >> (56 - 8 * i)) & 0xff);
  return k;
}
static inline uint64_t KeyIdFromSlice(const char* p, size_t n) {
  uint64_t id = 0;
  for (int i = 0; i < 8 && size_t(i) < n; ++i)
    id = (id << 8) | static_cast<unsigned char>(p[i]);
  return id;
}

static inline std::string MakeValue(uint64_t seed, uint32_t phase,
                                    uint64_t op_index, uint64_t key_id,
                                    size_t size) {
  std::string v(size, '\0');
  uint64_t x = seed ^ key_id ^ (uint64_t(phase) << 48) ^ op_index;
  for (size_t i = 0; i < size; ++i) v[i] = char(SplitMix64(x) & 0xff);
  return v;
}

static double Percentile(std::vector<double>& xs, double p) {
  if (xs.empty()) return 0.0;
  std::sort(xs.begin(), xs.end());
  double idx = p * (static_cast<double>(xs.size()) - 1.0);
  size_t lo = static_cast<size_t>(idx);
  size_t hi = std::min(lo + 1, xs.size() - 1);
  double frac = idx - static_cast<double>(lo);
  return xs[lo] * (1.0 - frac) + xs[hi] * frac;
}

static std::string JsonEscape(const std::string& s) {
  std::ostringstream out;
  for (unsigned char c : s) {
    switch (c) {
      case '\\':
        out << "\\\\";
        break;
      case '"':
        out << "\\\"";
        break;
      case '\b':
        out << "\\b";
        break;
      case '\f':
        out << "\\f";
        break;
      case '\n':
        out << "\\n";
        break;
      case '\r':
        out << "\\r";
        break;
      case '\t':
        out << "\\t";
        break;
      default:
        if (c < 0x20) {
          out << "\\u";
          const char* hex = "0123456789abcdef";
          out << "00" << hex[(c >> 4) & 0xf] << hex[c & 0xf];
        } else {
          out << char(c);
        }
    }
  }
  return out.str();
}

// Event listener

class MetricsListener final : public rocksdb::EventListener {
 public:
  std::atomic<uint64_t> flush_output_bytes{0};
  std::atomic<uint64_t> compaction_output_bytes{0};
  std::atomic<uint64_t> table_created_bytes{0};  // sanity cross-check
  std::atomic<uint64_t> compaction_events{0};    // diagnostic: # compactions
  std::atomic<uint64_t> intra_l0_compactions{0};
  std::atomic<uint64_t> failed_compactions{0};
  std::atomic<uint64_t> background_errors{0};

  void OnFlushCompleted(rocksdb::DB*,
                        const rocksdb::FlushJobInfo& info) override {
    uint64_t bytes = 0;
    std::error_code ec;
    if (!info.file_path.empty()) {
      bytes = static_cast<uint64_t>(fs::file_size(info.file_path, ec));
      if (ec) bytes = 0;
    }
    if (bytes == 0) {
      const auto& p = info.table_properties;
      bytes = p.data_size + p.index_size + p.filter_size;
    }
    flush_output_bytes.fetch_add(bytes, std::memory_order_relaxed);
  }
  void OnCompactionCompleted(rocksdb::DB*,
                             const rocksdb::CompactionJobInfo& info) override {
    if (!info.status.ok()) {
      failed_compactions.fetch_add(1, std::memory_order_relaxed);
      return;
    }
    compaction_events.fetch_add(1, std::memory_order_relaxed);
    if (info.base_input_level == 0 && info.output_level == 0) {
      intra_l0_compactions.fetch_add(1, std::memory_order_relaxed);
    }
    compaction_output_bytes.fetch_add(info.stats.total_output_bytes,
                                      std::memory_order_relaxed);
  }
  void OnBackgroundError(rocksdb::BackgroundErrorReason,
                         rocksdb::Status* bg_error) override {
    if (bg_error && !bg_error->ok()) {
      background_errors.fetch_add(1, std::memory_order_relaxed);
    }
  }
  void OnTableFileCreated(const rocksdb::TableFileCreationInfo& info) override {
    table_created_bytes.fetch_add(static_cast<uint64_t>(info.file_size),
                                  std::memory_order_relaxed);
  }

  void Reset() {
    flush_output_bytes.store(0, std::memory_order_relaxed);
    compaction_output_bytes.store(0, std::memory_order_relaxed);
    table_created_bytes.store(0, std::memory_order_relaxed);
    compaction_events.store(0, std::memory_order_relaxed);
    intra_l0_compactions.store(0, std::memory_order_relaxed);
    failed_compactions.store(0, std::memory_order_relaxed);
    background_errors.store(0, std::memory_order_relaxed);
  }
};

// Workload profiles

struct Profile {
  std::string name;
  uint64_t U;
  uint64_t p0, p1, p2, p3, p4, p5_reads, p5_scans, window;
  size_t wbuf_mib, tfs_mib, lbase_mib, maxcomp_mib, cache_mib;
  int l0_trigger, l0_slow, l0_stop, lmult, bg_jobs, num_levels, num_cfs;
};

static Profile EmptyProfile() {
  return {"", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
}

static uint64_t ScaleCount(uint64_t value, uint64_t num, uint64_t den) {
  return std::max<uint64_t>(1, (value * num + den - 1) / den);
}

static Profile ClampProfile(Profile p) {
  p.wbuf_mib = std::max<size_t>(2, p.wbuf_mib);
  p.tfs_mib = std::max<size_t>(2, p.tfs_mib);
  p.lbase_mib = std::max<size_t>(8, p.lbase_mib);
  p.maxcomp_mib = std::max<size_t>(16, p.maxcomp_mib);
  p.cache_mib = std::max<size_t>(16, p.cache_mib);
  p.l0_trigger = std::max(2, p.l0_trigger);
  p.l0_slow = std::max(p.l0_trigger + 3, p.l0_slow);
  p.l0_stop = std::max(p.l0_slow + 4, p.l0_stop);
  p.lmult = std::max(2, p.lmult);
  p.bg_jobs = std::max(1, p.bg_jobs);
  p.num_levels = std::max(4, p.num_levels);
  p.num_cfs = std::max(1, p.num_cfs);
  return p;
}

static Profile DeriveCaseProfile(Profile p, uint64_t seed) {
  if (p.name == "smoke") return p;
  uint64_t r = Rng(seed, 9, 0, 601);
  switch (r % 5) {
    case 0:
      p.wbuf_mib = std::max<size_t>(2, p.wbuf_mib / 2);
      p.tfs_mib = std::max<size_t>(2, p.tfs_mib / 2);
      p.l0_trigger = std::max(2, p.l0_trigger - 1);
      break;
    case 1:
      p.lbase_mib = std::max<size_t>(16, p.lbase_mib / 2);
      p.maxcomp_mib = std::max<size_t>(16, p.maxcomp_mib / 2);
      p.p5_scans = ScaleCount(p.p5_scans, 5, 4);
      break;
    case 2:
      p.cache_mib = std::max<size_t>(16, p.cache_mib / 2);
      p.p5_reads = ScaleCount(p.p5_reads, 6, 5);
      break;
    case 3:
      p.window = std::max<uint64_t>(1024, p.window / 2);
      p.p3 = ScaleCount(p.p3, 7, 6);
      p.p4 = ScaleCount(p.p4, 7, 6);
      break;
    case 4:
      p.bg_jobs = std::max(1, p.bg_jobs - 1);
      p.p2 = ScaleCount(p.p2, 6, 5);
      break;
  }
  uint64_t skew = 90 + ((r >> 8) % 21);  // 0.90x .. 1.10x
  p.p1 = ScaleCount(p.p1, skew, 100);
  p.p2 = ScaleCount(p.p2, 200 - skew, 100);
  p.p4 = ScaleCount(p.p4, 95 + ((r >> 16) % 16), 100);
  return ClampProfile(p);
}

static Profile GetProfile(const std::string& name, bool* ok = nullptr) {
  if (ok) *ok = true;
  if (name == "full")
    return {"full", 524288, 70000, 60000, 85000, 70000, 80000, 25000,
            2500,   4096,   4,     4,     16,    64,    48,    3,
            9,      18,     6,     2,     6,     1};
  if (name == "smoke")
    return {"smoke", 262144, 40000, 40000, 70000, 50000, 60000, 20000,
            1000,    2048,   4,     4,     16,    64,    32,    4,
            10,      20,     4,     2,     6,     1};
  if (name == "l0_pressure")
    return {"l0_pressure",
            1048576,
            120000,
            180000,
            300000,
            160000,
            180000,
            50000,
            3000,
            4096,
            4,
            4,
            16,
            64,
            64,
            3,
            8,
            16,
            4,
            2,
            6,
            1};
  if (name == "range_snapshot")
    return {"range_snapshot",
            1048576,
            140000,
            120000,
            320000,
            160000,
            220000,
            70000,
            3500,
            8192,
            8,
            8,
            32,
            128,
            64,
            4,
            10,
            20,
            8,
            3,
            6,
            1};
  if (name == "scanmix")
    return {"scanmix", 1572864, 180000, 120000, 180000, 220000, 300000, 140000,
            5000,      16384,   8,      8,      32,     128,    96,     4,
            10,        20,      8,      3,      6,      1};
  if (name == "multi_cf")
    return {"multi_cf", 524288, 90000, 120000, 170000, 130000, 160000, 60000,
            2500,       4096,   4,     4,      16,     64,     64,     4,
            10,         20,     4,     2,      6,      3};
  if (name == "time_series")
    return {"time_series",
            2097152,
            200000,
            180000,
            240000,
            220000,
            240000,
            80000,
            6000,
            8192,
            8,
            8,
            32,
            128,
            64,
            4,
            10,
            20,
            8,
            3,
            6,
            1};
  if (name == "difficulty")
    return {
        "difficulty", 1048576, 160000, 140000, 260000, 180000, 220000, 80000,
        4000,         8192,    4,      4,      16,     64,     64,     4,
        10,           20,      4,      2,      6,      1};
  if (name == "overlap_rewrite")
    return {"overlap_rewrite",
            1048576,
            160000,
            144000,
            144000,
            120000,
            120000,
            60000,
            25000,
            4096,
            8,
            4,
            16,
            64,
            64,
            4,
            10,
            20,
            4,
            1,
            6,
            1};
  if (ok) *ok = false;
  return EmptyProfile();
}

static bool IsHiddenOrHardProfile(const std::string& name) {
  return name == "difficulty" || name == "full";
}

static rocksdb::Options MakeOptions(const Profile& pf,
                                    std::shared_ptr<MetricsListener> listener) {
  rocksdb::Options o;
  o.create_if_missing = true;
  o.compaction_style = rocksdb::kCompactionStyleLevel;
  o.compression = rocksdb::kNoCompression;
  o.num_levels = pf.num_levels;
  o.write_buffer_size = pf.wbuf_mib << 20;
  o.max_write_buffer_number = 4;
  o.min_write_buffer_number_to_merge = 1;
  o.level0_file_num_compaction_trigger = pf.l0_trigger;
  o.level0_slowdown_writes_trigger = pf.l0_slow;
  o.level0_stop_writes_trigger = pf.l0_stop;
  o.target_file_size_base = pf.tfs_mib << 20;
  o.target_file_size_multiplier = 1;
  o.max_bytes_for_level_base = pf.lbase_mib << 20;
  o.max_bytes_for_level_multiplier = pf.lmult;
  o.max_compaction_bytes = pf.maxcomp_mib << 20;
  o.max_background_jobs = 1;
  o.max_subcompactions = 1;
  o.use_direct_reads = false;
  o.use_direct_io_for_flush_and_compaction = false;
  o.statistics = rocksdb::CreateDBStatistics();
  if (listener) o.listeners.emplace_back(listener);
  rocksdb::BlockBasedTableOptions topt;
  topt.block_cache = rocksdb::NewLRUCache(pf.cache_mib << 20);
  topt.read_amp_bytes_per_bit = 16;
  o.table_factory.reset(rocksdb::NewBlockBasedTableFactory(topt));
  return o;
}

struct DataDigest {
  uint64_t h1 = 1469598103934665603ULL;
  uint64_t h2 = 1099511628211ULL ^ 0xff51afd7ed558ccdULL;
  uint64_t entries = 0;
  uint64_t bytes = 0;
  bool ok = true;
};

static void DigestBytes(DataDigest* digest, const char* data, size_t size) {
  const uint64_t encoded_size = static_cast<uint64_t>(size);
  const char* size_bytes = reinterpret_cast<const char*>(&encoded_size);
  for (size_t i = 0; i < sizeof(encoded_size); ++i) {
    const unsigned char c = static_cast<unsigned char>(size_bytes[i]);
    digest->h1 = (digest->h1 ^ c) * 1099511628211ULL;
    digest->h2 = (digest->h2 ^ c) * 0x100000001b3ULL;
    digest->h2 = (digest->h2 << 7) | (digest->h2 >> 57);
  }
  for (size_t i = 0; i < size; ++i) {
    const unsigned char c = static_cast<unsigned char>(data[i]);
    digest->h1 = (digest->h1 ^ c) * 1099511628211ULL;
    digest->h2 = (digest->h2 ^ c) * 0x100000001b3ULL;
    digest->h2 = (digest->h2 << 7) | (digest->h2 >> 57);
  }
}

static DataDigest CollectDataDigest(
    rocksdb::DB* db, const std::vector<rocksdb::ColumnFamilyHandle*>& handles,
    const std::vector<std::string>& cf_names) {
  DataDigest digest;
  rocksdb::ReadOptions read_options;
  for (size_t cf = 0; cf < handles.size(); ++cf) {
    DigestBytes(&digest, cf_names[cf].data(), cf_names[cf].size());
    std::unique_ptr<rocksdb::Iterator> it(
        db->NewIterator(read_options, handles[cf]));
    for (it->SeekToFirst(); it->Valid(); it->Next()) {
      DigestBytes(&digest, it->key().data(), it->key().size());
      DigestBytes(&digest, it->value().data(), it->value().size());
      ++digest.entries;
      digest.bytes += it->key().size() + it->value().size();
    }
    if (!it->status().ok()) digest.ok = false;
  }
  return digest;
}

static int RunTrustedResidual(const std::string& db_dir,
                              const std::string& out_path, const Profile& pf) {
  auto write_failure = [&](const std::string& reason) {
    std::ofstream out(out_path);
    out << "{\"ok\":false,\"fail_reason\":\"" << JsonEscape(reason) << "\"}\n";
  };

  auto listener = std::make_shared<MetricsListener>();
  rocksdb::Options options = MakeOptions(pf, listener);
  options.create_if_missing = false;
  options.disable_auto_compactions = true;
  std::vector<std::string> cf_names;
  rocksdb::Status status = rocksdb::DB::ListColumnFamilies(
      rocksdb::DBOptions(options), db_dir, &cf_names);
  if (!status.ok() || cf_names.empty()) {
    write_failure("list-column-families: " + status.ToString());
    return 0;
  }

  std::vector<rocksdb::ColumnFamilyDescriptor> descriptors;
  descriptors.reserve(cf_names.size());
  for (const auto& name : cf_names) {
    descriptors.emplace_back(name, rocksdb::ColumnFamilyOptions(options));
  }
  std::vector<rocksdb::ColumnFamilyHandle*> handles;
  rocksdb::DB* db = nullptr;
#if ROCKSDB_VERSION_GE(11, 0, 0)
  std::unique_ptr<rocksdb::DB> db_owner;
  status = rocksdb::DB::Open(rocksdb::DBOptions(options), db_dir, descriptors,
                             &handles, &db_owner);
  db = db_owner.get();
#else
  status = rocksdb::DB::Open(rocksdb::DBOptions(options), db_dir, descriptors,
                             &handles, &db);
#endif
  if (!status.ok()) {
    write_failure("open-trusted-drain: " + status.ToString());
    return 0;
  }

  bool ok = true;
  std::string fail_reason;
  const DataDigest before_digest = CollectDataDigest(db, handles, cf_names);
  if (!before_digest.ok) {
    ok = false;
    fail_reason = "pre-residual-iterator-failed";
  }

  bool converged = false;
  int passes = 0;
  uint64_t previous_output = 0;
  for (int pass = 0; pass < 3 && ok; ++pass) {
    status = db->EnableAutoCompaction(handles);
    if (!status.ok()) {
      ok = false;
      fail_reason = "enable-auto-compaction: " + status.ToString();
      break;
    }
    rocksdb::WaitForCompactOptions wait;
    wait.flush = false;
    status = db->WaitForCompact(wait);
    if (!status.ok()) {
      ok = false;
      fail_reason = "wait-trusted-residual: " + status.ToString();
      break;
    }
    for (auto* handle : handles) {
      status = db->SetOptions(handle, {{"disable_auto_compactions", "true"}});
      if (!status.ok()) {
        ok = false;
        fail_reason = "disable-auto-compaction: " + status.ToString();
        break;
      }
    }
    if (!ok) break;
    ++passes;
    const uint64_t current_output =
        listener->compaction_output_bytes.load(std::memory_order_relaxed);
    if (current_output == previous_output) {
      converged = true;
      break;
    }
    previous_output = current_output;
  }
  if (ok && !converged) {
    ok = false;
    fail_reason = "trusted-residual-did-not-converge";
  }

  uint64_t l0_files = 0;
  uint64_t upper_level_files = 0;
  uint64_t upper_level_bytes = 0;
  uint64_t final_files = 0;
  std::vector<rocksdb::ColumnFamilyMetaData> metadata;
  db->GetAllColumnFamilyMetaData(&metadata);
  for (const auto& cf : metadata) {
    for (const auto& level : cf.levels) {
      final_files += level.files.size();
      if (level.level == 0) l0_files += level.files.size();
      if (level.level < pf.num_levels - 1) {
        upper_level_files += level.files.size();
        upper_level_bytes += level.size;
      }
    }
  }
  const uint64_t compaction_bytes =
      listener->compaction_output_bytes.load(std::memory_order_relaxed);
  const uint64_t failed_compactions =
      listener->failed_compactions.load(std::memory_order_relaxed);
  const uint64_t background_errors =
      listener->background_errors.load(std::memory_order_relaxed);
  const DataDigest after_digest = CollectDataDigest(db, handles, cf_names);
  if (ok && (!after_digest.ok || before_digest.h1 != after_digest.h1 ||
             before_digest.h2 != after_digest.h2 ||
             before_digest.entries != after_digest.entries ||
             before_digest.bytes != after_digest.bytes)) {
    ok = false;
    fail_reason = "trusted-residual-changed-logical-data";
  }

  for (auto* handle : handles) db->DestroyColumnFamilyHandle(handle);
#if ROCKSDB_VERSION_GE(11, 0, 0)
  db_owner.reset();
#else
  delete db;
#endif

  uint64_t table_bytes = 0;
  std::error_code walk_ec;
  for (const auto& entry : fs::directory_iterator(db_dir, walk_ec)) {
    if (walk_ec) break;
    if (!entry.is_regular_file(walk_ec) || walk_ec) continue;
    const auto extension = entry.path().extension();
    if (extension != ".sst" && extension != ".blob") continue;
    table_bytes += static_cast<uint64_t>(entry.file_size(walk_ec));
    if (walk_ec) break;
  }
  if (walk_ec && ok) {
    ok = false;
    fail_reason = "table-file-size: " + walk_ec.message();
  }
  if ((failed_compactions != 0 || background_errors != 0) && ok) {
    ok = false;
    fail_reason = "trusted-drain-background-error";
  }

  std::ofstream out(out_path);
  out << "{\n  \"ok\": " << (ok ? "true" : "false") << ",\n";
  out << "  \"fail_reason\": \"" << JsonEscape(fail_reason) << "\",\n";
  out << "  \"compaction_output_bytes\": " << compaction_bytes << ",\n";
  out << "  \"final_table_bytes\": " << table_bytes << ",\n";
  out << "  \"final_files\": " << final_files << ",\n";
  out << "  \"l0_files\": " << l0_files << ",\n";
  out << "  \"upper_level_files\": " << upper_level_files << ",\n";
  out << "  \"upper_level_bytes\": " << upper_level_bytes << ",\n";
  out << "  \"passes\": " << passes << ",\n";
  out << "  \"digest_entries\": " << after_digest.entries << ",\n";
  out << "  \"digest_bytes\": " << after_digest.bytes << "\n}\n";
  return 0;
}

// Workload sampling

static uint64_t MovingHotCenter(uint64_t seed, uint32_t phase,
                                uint64_t op_index, uint64_t U,
                                uint64_t window) {
  const uint64_t period = 50000;
  uint64_t steps = op_index / period;
  uint64_t center = Rng(seed, phase, 0, 99) % U;
  uint64_t span = std::max<uint64_t>(window, U / 64);
  for (uint64_t i = 0; i < steps; ++i) {
    int64_t delta =
        int64_t(Rng(seed, phase, i, 100) % (2 * span)) - int64_t(span);
    int64_t c = (int64_t(center) + delta) % int64_t(U);
    if (c < 0) c += int64_t(U);
    center = uint64_t(c);
  }
  return center;
}
static uint64_t SampleHot(uint64_t seed, uint32_t phase, uint64_t op_index,
                          uint64_t center, uint64_t window, uint64_t U) {
  uint64_t off = Rng(seed, phase, op_index, 10) % std::max<uint64_t>(1, window);
  uint64_t start = (center + U - window / 2) % U;
  return (start + off) % U;
}
static uint64_t SampleHeavyTail(uint64_t seed, uint32_t phase,
                                uint64_t op_index, uint64_t U) {
  uint64_t r1 = Rng(seed, phase, op_index, 20) % U;
  uint64_t r2 = Rng(seed, phase, op_index, 21) % U;
  uint64_t r3 = Rng(seed, phase, op_index, 22) % U;
  return std::min(r1, std::min(r2, r3));
}
static size_t PickValueSize(uint64_t seed, uint32_t phase, uint64_t op_index,
                            const std::vector<std::pair<int, size_t>>& mix) {
  int r = int(Rng(seed, phase, op_index, 30) % 100), acc = 0;
  for (auto& m : mix) {
    acc += m.first;
    if (r < acc) return m.second;
  }
  return mix.back().second;
}

struct OracleEntry {
  uint32_t size = 0;
  uint64_t h1 = 0, h2 = 0;
  bool present = false;
};

struct SnapshotSample {
  size_t cf = 0;
  uint64_t key_id = 0;
  bool present = false;
  uint32_t size = 0;
  uint64_t h1 = 0, h2 = 0;
};

struct LsmMetrics {
  uint64_t pending = 0;
  uint64_t lsm_bytes = 0;
  uint64_t l0_base_overlap_bytes = 0;
  uint64_t active_memtable_bytes = 0;
  uint64_t active_memtable_entries = 0;
  uint64_t immutable_memtables = 0;
  uint64_t fingerprint = 1469598103934665603ULL;
  uint64_t level_bytes[6] = {0, 0, 0, 0, 0, 0};
  uint64_t level_files[6] = {0, 0, 0, 0, 0, 0};
  std::vector<uint64_t> l0_files_by_cf;
  uint64_t column_families = 0;
};

static void LoadCaseFile(const std::string& path, uint64_t* seed,
                         std::string* profile_name) {
  std::ifstream in(path);
  std::string line;
  while (std::getline(in, line)) {
    const size_t eq = line.find('=');
    if (eq == std::string::npos) continue;
    const std::string key = line.substr(0, eq);
    const std::string value = line.substr(eq + 1);
    if (key == "seed")
      *seed = std::stoull(value);
    else if (key == "profile")
      *profile_name = value;
  }
}

int main(int argc, char** argv) {
  std::string db_dir, out_path, case_file, profile_name = "difficulty";
  uint64_t seed = 1;
  bool trusted_drain = false;
  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    auto nxt = [&]() -> std::string { return (i + 1 < argc) ? argv[++i] : ""; };
    if (a == "--db")
      db_dir = nxt();
    else if (a == "--seed")
      seed = std::stoull(nxt());
    else if (a == "--profile")
      profile_name = nxt();
    else if (a == "--out")
      out_path = nxt();
    else if (a == "--case-file")
      case_file = nxt();
    else if (a == "--trusted-residual")
      trusted_drain = true;
  }
  if (db_dir.empty() || out_path.empty()) {
    std::fprintf(stderr, "usage: --db DIR --out JSON [--case-file PATH]\n");
    return 2;
  }
  if (!case_file.empty()) {
    LoadCaseFile(case_file, &seed, &profile_name);
    std::remove(case_file.c_str());
  }

  bool profile_ok = false;
  const Profile base_pf = GetProfile(profile_name, &profile_ok);
  if (!profile_ok) {
    std::ofstream o(out_path);
    o << "{\"ok\":false,\"fail_reason\":\"unknown-profile: "
      << JsonEscape(profile_name) << "\"}\n";
    return 0;
  }
  const Profile pf = DeriveCaseProfile(base_pf, seed);
  if (trusted_drain) return RunTrustedResidual(db_dir, out_path, pf);
  const uint64_t U = pf.U;
  const bool hidden_or_hard_profile = IsHiddenOrHardProfile(profile_name);
  const uint64_t mix_bits = hidden_or_hard_profile ? Rng(seed, 8, 0, 713) : 0;
  const bool mixed_range_snapshot =
      hidden_or_hard_profile && ((mix_bits % 3) != 1);
  const bool mixed_scan = hidden_or_hard_profile && (((mix_bits / 3) % 3) != 1);
  const bool mixed_time_series =
      hidden_or_hard_profile &&
      ((((mix_bits / 9) % 4) == 0) || profile_name == "full");
  const bool snapshot_profile =
      profile_name == "range_snapshot" || profile_name == "multi_cf" ||
      profile_name == "full" || mixed_range_snapshot ||
      (hidden_or_hard_profile && pf.num_cfs > 1 && ((mix_bits >> 5) & 1));
  const bool range_profile = profile_name == "range_snapshot" ||
                             profile_name == "full" || mixed_range_snapshot;
  const bool scan_profile =
      profile_name == "scanmix" || profile_name == "full" || mixed_scan;
  const bool time_series_profile = profile_name == "time_series" ||
                                   profile_name == "full" || mixed_time_series;
  const bool overlap_rewrite_profile = profile_name == "overlap_rewrite";

  std::error_code ec;
  fs::remove_all(db_dir, ec);
  fs::create_directories(db_dir, ec);

  auto listener = std::make_shared<MetricsListener>();
  rocksdb::Options options = MakeOptions(pf, listener);
  rocksdb::DB* db = nullptr;
#if ROCKSDB_VERSION_GE(11, 0, 0)
  std::unique_ptr<rocksdb::DB> db_owner;
  rocksdb::Status s = rocksdb::DB::Open(options, db_dir, &db_owner);
  db = db_owner.get();
#else
  rocksdb::Status s = rocksdb::DB::Open(options, db_dir, &db);
#endif
  if (!s.ok()) {
    std::ofstream o(out_path);
    o << "{\"ok\":false,\"fail_reason\":\"open: " << JsonEscape(s.ToString())
      << "\"}\n";
    return 0;
  }
  std::vector<rocksdb::ColumnFamilyHandle*> cf_handles;
  std::vector<rocksdb::ColumnFamilyHandle*> owned_cf_handles;
  cf_handles.push_back(db->DefaultColumnFamily());
  rocksdb::ColumnFamilyOptions cf_opts(options);
  for (int i = 1; i < pf.num_cfs; ++i) {
    rocksdb::ColumnFamilyHandle* h = nullptr;
    rocksdb::Status cfs =
        db->CreateColumnFamily(cf_opts, "cf" + std::to_string(i), &h);
    if (!cfs.ok()) {
      std::ofstream o(out_path);
      o << "{\"ok\":false,\"fail_reason\":\"create-cf: "
        << JsonEscape(cfs.ToString()) << "\"}\n";
#if ROCKSDB_VERSION_GE(11, 0, 0)
      db_owner.reset();
#else
      delete db;
#endif
      return 0;
    }
    cf_handles.push_back(h);
    owned_cf_handles.push_back(h);
  }
  std::vector<std::vector<OracleEntry>> oracle(cf_handles.size(),
                                               std::vector<OracleEntry>(U));

  rocksdb::WriteOptions wo;
  wo.disableWAL =
      true;  // measuring compaction policy; clean close before reopen
  rocksdb::ReadOptions ro;

  std::vector<double> get_lat_us, scan_lat_us;
  uint64_t user_put_bytes = 0;
  int64_t live = 0;
  bool correctness_ok = true;
  std::string fail_reason;
  const rocksdb::Snapshot* held_snapshot = nullptr;
  std::vector<SnapshotSample> snapshot_samples;
  std::vector<std::vector<uint8_t>> modified_since_snapshot;

  auto fail = [&](const std::string& reason) {
    if (correctness_ok) {
      correctness_ok = false;
      fail_reason = reason;
    }
  };
  auto check_background_errors = [&](const std::string& where) {
    uint64_t bg_count = 0;
    if (!db->GetIntProperty(rocksdb::DB::Properties::kBackgroundErrors,
                            &bg_count)) {
      fail("property-background-errors: " + where);
    } else if (bg_count > 0) {
      fail("background-errors: " + where + ": " + std::to_string(bg_count));
    }
    uint64_t listener_bg =
        listener->background_errors.load(std::memory_order_relaxed);
    if (listener_bg > 0) {
      fail("listener-background-error: " + where + ": " +
           std::to_string(listener_bg));
    }
    uint64_t failed_compactions =
        listener->failed_compactions.load(std::memory_order_relaxed);
    if (failed_compactions > 0) {
      fail("compaction-error: " + where + ": " +
           std::to_string(failed_compactions));
    }
  };
  auto set_auto_compactions = [&](bool enabled, const std::string& where) {
    for (auto* h : cf_handles) {
      rocksdb::Status changed;
      if (enabled) {
        changed = db->SetOptions(
            h, {{"level0_slowdown_writes_trigger", std::to_string(pf.l0_slow)},
                {"level0_stop_writes_trigger", std::to_string(pf.l0_stop)}});
      } else {
        changed =
            db->SetOptions(h, {{"disable_auto_compactions", "true"},
                               {"level0_slowdown_writes_trigger", "1000000"},
                               {"level0_stop_writes_trigger", "1000000"}});
      }
      if (!changed.ok()) {
        fail("set-compaction-mode-" + where + ": " + changed.ToString());
      }
    }
    if (enabled) {
      rocksdb::Status status = db->EnableAutoCompaction(cf_handles);
      if (!status.ok()) {
        fail("enable-auto-compaction-" + where + ": " + status.ToString());
      }
    }
  };
  auto flush_memtables = [&](const std::string& where) {
    rocksdb::FlushOptions flush;
    flush.wait = true;
    for (auto* h : cf_handles) {
      rocksdb::Status status = db->Flush(flush, h);
      if (!status.ok()) fail("flush-" + where + ": " + status.ToString());
    }
  };
  auto run_compaction_cycle = [&](const std::string& where) {
    flush_memtables(where);
    set_auto_compactions(true, where);
    rocksdb::WaitForCompactOptions wait;
    wait.flush = true;
    rocksdb::Status status = db->WaitForCompact(wait);
    if (!status.ok()) fail("wait-" + where + ": " + status.ToString());
    check_background_errors(where);
    set_auto_compactions(false, where);
  };
  auto cf_for = [&](uint32_t ph, uint64_t op, uint64_t kid) -> size_t {
    if (cf_handles.size() == 1) return 0;
    return size_t(Rng(seed, ph, op ^ (kid * 1315423911ULL), 77) %
                  cf_handles.size());
  };

  auto put = [&](uint32_t ph, uint64_t op, uint64_t kid, size_t vsz) {
    size_t cf = cf_for(ph, op, kid);
    std::string k = MakeKey(kid, seed), v = MakeValue(seed, ph, op, kid, vsz);
    rocksdb::Status st = db->Put(wo, cf_handles[cf], k, v);
    if (!st.ok()) {
      fail("put: " + st.ToString());
      return;
    }
    auto& e = oracle[cf][kid];
    if (e.present)
      live += int64_t(vsz) - int64_t(e.size);
    else
      live += int64_t(16 + vsz);
    auto h = Hash128(v);
    e.present = true;
    e.size = uint32_t(vsz);
    e.h1 = h.first;
    e.h2 = h.second;
    if (!modified_since_snapshot.empty()) modified_since_snapshot[cf][kid] = 1;
    user_put_bytes += k.size() + v.size();
  };
  auto del = [&](uint32_t ph, uint64_t op, uint64_t kid) {
    size_t cf = cf_for(ph, op, kid);
    rocksdb::Status st = db->Delete(wo, cf_handles[cf], MakeKey(kid, seed));
    if (!st.ok()) {
      fail("delete: " + st.ToString());
      return;
    }
    auto& e = oracle[cf][kid];
    if (e.present) live -= int64_t(16 + e.size);
    e.present = false;
    e.size = 0;
    if (!modified_since_snapshot.empty()) modified_since_snapshot[cf][kid] = 1;
  };
  auto delrange = [&](uint32_t ph, uint64_t op, uint64_t b, uint64_t e2) {
    if (e2 > U) e2 = U;
    if (b >= e2) return;
    size_t cf = cf_for(ph, op, b);
    rocksdb::Status st = db->DeleteRange(wo, cf_handles[cf], MakeKey(b, seed),
                                         MakeKey(e2, seed));
    if (!st.ok()) {
      fail("delete-range: " + st.ToString());
      return;
    }
    size_t targeted = 0;
    if (held_snapshot && !modified_since_snapshot.empty()) {
      for (uint64_t k = b;
           k < e2 && targeted < 8 && snapshot_samples.size() < 8192; ++k) {
        const auto& e = oracle[cf][k];
        if (!modified_since_snapshot[cf][k] && e.present) {
          SnapshotSample sample;
          sample.cf = cf;
          sample.key_id = k;
          sample.present = true;
          sample.size = e.size;
          sample.h1 = e.h1;
          sample.h2 = e.h2;
          snapshot_samples.push_back(sample);
          ++targeted;
        }
      }
    }
    for (uint64_t k = b; k < e2; ++k) {
      auto& e = oracle[cf][k];
      if (e.present) live -= int64_t(16 + e.size);
      e.present = false;
      e.size = 0;
      if (!modified_since_snapshot.empty()) modified_since_snapshot[cf][k] = 1;
    }
  };
  auto timed_get = [&](uint32_t ph, uint64_t op, uint64_t kid) {
    size_t cf = cf_for(ph, op, kid);
    std::string got;
    auto t0 = Clock::now();
    rocksdb::Status st = db->Get(ro, cf_handles[cf], MakeKey(kid, seed), &got);
    get_lat_us.push_back(
        std::chrono::duration<double, std::micro>(Clock::now() - t0).count());
    if (!st.ok() && !st.IsNotFound()) fail("get: " + st.ToString());
  };
  auto timed_scan = [&](uint32_t ph, uint64_t op, uint64_t start, int len) {
    size_t cf = cf_for(ph, op, start);
    auto t0 = Clock::now();
    std::unique_ptr<rocksdb::Iterator> it(db->NewIterator(ro, cf_handles[cf]));
    it->Seek(MakeKey(start, seed));
    int c = 0;
    while (it->Valid() && c < len) {
      it->Next();
      ++c;
    }
    scan_lat_us.push_back(
        std::chrono::duration<double, std::micro>(Clock::now() - t0).count());
    if (!it->status().ok()) fail("scan-iter: " + it->status().ToString());
  };

  std::vector<std::pair<int, size_t>> mix1 = {{75, 400}, {20, 1024}, {5, 4096}};
  std::vector<std::pair<int, size_t>> mix2 = {{90, 128}, {10, 2048}};
  std::vector<std::pair<int, size_t>> mix4 = {{80, 128}, {15, 1024}, {5, 4096}};

  double ops_per_sec[5] = {0, 0, 0, 0, 0};
  auto capture_snapshot = [&]() {
    held_snapshot = db->GetSnapshot();
    snapshot_samples.clear();
    modified_since_snapshot.assign(cf_handles.size(),
                                   std::vector<uint8_t>(U, 0));
    for (size_t cf = 0; cf < cf_handles.size(); ++cf) {
      for (uint64_t i = 0; i < 256; ++i) {
        uint64_t kid = Rng(seed, 6, i + cf * 1000, 44) % U;
        const auto& e = oracle[cf][kid];
        SnapshotSample sample;
        sample.cf = cf;
        sample.key_id = kid;
        sample.present = e.present;
        sample.size = e.size;
        sample.h1 = e.h1;
        sample.h2 = e.h2;
        snapshot_samples.push_back(sample);
      }
    }
  };

  auto verify_snapshot = [&](bool release_after) {
    if (!held_snapshot) return;
    rocksdb::ReadOptions sro = ro;
    sro.snapshot = held_snapshot;
    for (const auto& sample : snapshot_samples) {
      std::string got;
      rocksdb::Status st = db->Get(sro, cf_handles[sample.cf],
                                   MakeKey(sample.key_id, seed), &got);
      if (sample.present) {
        auto h = Hash128(got);
        if (!st.ok() || got.size() != sample.size || h.first != sample.h1 ||
            h.second != sample.h2) {
          fail("snapshot-mismatch present");
          break;
        }
      } else if (!st.IsNotFound()) {
        fail("snapshot-mismatch deleted");
        break;
      }
    }
    if (release_after) {
      db->ReleaseSnapshot(held_snapshot);
      held_snapshot = nullptr;
    }
  };

  auto collect_lsm = [&]() {
    LsmMetrics m;
    for (auto* h : cf_handles) {
      uint64_t value = 0;
      if (!db->GetIntProperty(h, "rocksdb.estimate-pending-compaction-bytes",
                              &value))
        fail("property-pending");
      m.pending += value;
      value = 0;
      if (!db->GetIntProperty(h, "rocksdb.cur-size-active-mem-table", &value))
        fail("property-active-memtable");
      m.active_memtable_bytes += value;
      value = 0;
      if (!db->GetIntProperty(h, "rocksdb.num-entries-active-mem-table",
                              &value))
        fail("property-active-memtable-entries");
      m.active_memtable_entries += value;
      value = 0;
      if (!db->GetIntProperty(h, "rocksdb.num-immutable-mem-table", &value))
        fail("property-immutable-memtable");
      m.immutable_memtables += value;
    }

    std::vector<rocksdb::ColumnFamilyMetaData> metadata;
    db->GetAllColumnFamilyMetaData(&metadata);
    m.column_families = metadata.size();
    if (metadata.size() != cf_handles.size()) {
      fail("metadata-column-family-count");
    }
    for (const auto& cf : metadata) {
      auto mix_u64 = [&m](uint64_t value) {
        m.fingerprint ^= value + 0x9e3779b97f4a7c15ULL + (m.fingerprint << 6) +
                         (m.fingerprint >> 2);
      };
      auto mix_string = [&m](const std::string& value) {
        for (unsigned char c : value) {
          m.fingerprint = (m.fingerprint ^ c) * 1099511628211ULL;
        }
      };
      mix_string(cf.name);
      m.lsm_bytes += cf.size + cf.blob_file_size;
      const rocksdb::LevelMetaData* l0 = nullptr;
      const rocksdb::LevelMetaData* base = nullptr;
      for (const auto& level : cf.levels) {
        if (level.level < 0 || level.level >= 6) continue;
        mix_u64(static_cast<uint64_t>(level.level));
        mix_u64(level.size);
        m.level_bytes[level.level] += level.size;
        m.level_files[level.level] += level.files.size();
        for (const auto& file : level.files) {
          mix_u64(file.size);
          mix_string(file.smallestkey);
          mix_string(file.largestkey);
        }
        if (level.level == 0) l0 = &level;
        if (level.level > 0 && base == nullptr && !level.files.empty()) {
          base = &level;
        }
      }
      m.l0_files_by_cf.push_back(l0 == nullptr ? 0 : l0->files.size());
      if (l0 != nullptr && base != nullptr) {
        auto user_key = [](const std::string& internal_key) {
          return internal_key.substr(0, internal_key.size() >= 8
                                            ? internal_key.size() - 8
                                            : internal_key.size());
        };
        for (const auto& base_file : base->files) {
          const std::string base_smallest = user_key(base_file.smallestkey);
          const std::string base_largest = user_key(base_file.largestkey);
          for (const auto& l0_file : l0->files) {
            const std::string l0_smallest = user_key(l0_file.smallestkey);
            const std::string l0_largest = user_key(l0_file.largestkey);
            if (base_smallest <= l0_largest && l0_smallest <= base_largest) {
              m.l0_base_overlap_bytes += base_file.size;
              break;
            }
          }
        }
      }
    }
    return m;
  };

  auto same_lsm = [](const LsmMetrics& a, const LsmMetrics& b) {
    if (a.pending != b.pending || a.lsm_bytes != b.lsm_bytes ||
        a.l0_base_overlap_bytes != b.l0_base_overlap_bytes ||
        a.active_memtable_bytes != b.active_memtable_bytes ||
        a.active_memtable_entries != b.active_memtable_entries ||
        a.immutable_memtables != b.immutable_memtables ||
        a.fingerprint != b.fingerprint ||
        a.l0_files_by_cf != b.l0_files_by_cf ||
        a.column_families != b.column_families) {
      return false;
    }
    for (int level = 0; level < 6; ++level) {
      if (a.level_bytes[level] != b.level_bytes[level] ||
          a.level_files[level] != b.level_files[level]) {
        return false;
      }
    }
    return true;
  };

  auto collect_paused_lsm = [&](const std::string& where) {
    LsmMetrics first;
    rocksdb::Status paused = db->PauseBackgroundWork();
    if (!paused.ok()) {
      fail("pause-background-" + where + ": " + paused.ToString());
      return first;
    }
    first = collect_lsm();
    const LsmMetrics second = collect_lsm();
    if (!same_lsm(first, second)) {
      fail("unstable-metadata-" + where);
    }
    rocksdb::Status resumed = db->ContinueBackgroundWork();
    if (!resumed.ok()) {
      fail("resume-background-" + where + ": " + resumed.ToString());
    }
    return second;
  };

  auto percentile_copy = [](const std::vector<double>& xs, double p) {
    std::vector<double> copy(xs);
    return Percentile(copy, p);
  };

  auto table_file_bytes = [&]() {
    uint64_t bytes = 0;
    std::error_code walk_ec;
    for (const auto& entry : fs::directory_iterator(db_dir, walk_ec)) {
      if (walk_ec) break;
      if (!entry.is_regular_file(walk_ec) || walk_ec) continue;
      const auto extension = entry.path().extension();
      if (extension != ".sst" && extension != ".blob") continue;
      bytes += static_cast<uint64_t>(entry.file_size(walk_ec));
      if (walk_ec) break;
    }
    if (walk_ec) fail("table-file-size: " + walk_ec.message());
    return bytes;
  };

  uint64_t base_fingerprint = 0;
  // Phase 0: build a quiescent starting LSM, then reset all scored counters.
  {
    set_auto_compactions(false, "phase0");
    if (overlap_rewrite_profile) {
      const uint64_t band_width = U / 4;
      for (uint64_t op = 0; op < pf.p0; ++op) {
        const uint64_t draw = Rng(seed, 0, op, 101) % 100;
        const uint64_t band = draw < 50 ? 0 : 1 + (Rng(seed, 0, op, 102) % 3);
        const uint64_t kid =
            band * band_width + (Rng(seed, 0, op, 103) % band_width);
        put(0, op, kid, band == 0 ? 1024 : 128);
      }
    } else {
      uint64_t step = 2654435761ULL % U;
      if (step == 0) step = 1;
      uint64_t cur = Rng(seed, 0, 0, 1) % U;
      for (uint64_t op = 0; op < pf.p0; ++op) {
        cur = (cur + step) % U;
        put(0, op, cur, 400);
      }
    }
    rocksdb::FlushOptions fo;
    fo.wait = true;
    for (auto* h : cf_handles) {
      rocksdb::Status fst = db->Flush(fo, h);
      if (!fst.ok()) fail("flush-phase0: " + fst.ToString());
    }
    rocksdb::CompactRangeOptions compact;
    compact.change_level = true;
    compact.target_level = pf.num_levels - 1;
    for (auto* h : cf_handles) {
      rocksdb::Status cst = db->CompactRange(compact, h, nullptr, nullptr);
      if (!cst.ok()) fail("compact-phase0: " + cst.ToString());
    }
    rocksdb::WaitForCompactOptions wfc;
    wfc.flush = true;
    rocksdb::Status wst = db->WaitForCompact(wfc);
    if (!wst.ok()) fail("wait-phase0: " + wst.ToString());
    check_background_errors("phase0");
    const LsmMetrics base = collect_paused_lsm("phase0");
    base_fingerprint = base.fingerprint;
    uint64_t base_files = 0;
    for (int level = 1; level < 6; ++level) {
      base_files += base.level_files[level];
    }
    if (base_files == 0) fail("phase0-base-level-empty");
    listener->Reset();
    rocksdb::Status reset = options.statistics->Reset();
    if (!reset.ok()) fail("reset-statistics: " + reset.ToString());
    user_put_bytes = 0;
  }
  // Phase 1: uniform ingest + mild overwrite.
  {
    uint32_t ph = 1;
    auto t0 = Clock::now();
    const uint64_t append_base = Rng(seed, ph, 0, 62) % U;
    for (uint64_t op = 0; op < pf.p1; ++op) {
      if (overlap_rewrite_profile) {
        const uint64_t batch_size = 12000;
        const uint64_t band = ((op / batch_size) + 1) % 4;
        const uint64_t band_width = U / 4;
        const uint64_t kid =
            band * band_width + (Rng(seed, ph, op, 104) % band_width);
        put(ph, op, kid, 400);
        if ((op + 1) % batch_size == 0) {
          flush_memtables("phase1-band");
        }
        continue;
      }
      uint64_t kid =
          time_series_profile
              ? ((append_base + op + (Rng(seed, ph, op, 63) % 64)) % U)
              : (Rng(seed, ph, op, 2) % U);
      put(ph, op, kid,
          PickValueSize(seed, ph, op, time_series_profile ? mix4 : mix1));
    }
    ops_per_sec[1] =
        double(pf.p1) /
        std::max(1e-6,
                 std::chrono::duration<double>(Clock::now() - t0).count());
    check_background_errors("phase1");
  }
  run_compaction_cycle("phase1");
  // Phase 2: moving hot window.
  {
    uint32_t ph = 2;
    auto t0 = Clock::now();
    for (uint64_t op = 0; op < pf.p2; ++op) {
      if (overlap_rewrite_profile) {
        const uint64_t batch_size = 12000;
        const uint64_t band = ((op / batch_size) + 2) % 4;
        const uint64_t band_width = U / 4;
        const uint64_t kid =
            band * band_width + (Rng(seed, ph, op, 105) % band_width);
        put(ph, op, kid, 400);
        if ((op + 1) % batch_size == 0) {
          flush_memtables("phase2-band");
        }
        continue;
      }
      if (time_series_profile) {
        uint64_t tail = (pf.p0 + op * 3 + (Rng(seed, ph, op, 61) % 256)) % U;
        uint64_t cl_ts = Rng(seed, ph, op, 62) % 100;
        if (cl_ts < 78) {
          put(ph, op, tail, PickValueSize(seed, ph, op, mix4));
        } else if (cl_ts < 93) {
          timed_get(ph, op,
                    Rng(seed, ph, op, 63) % std::max<uint64_t>(1, U / 8));
        } else {
          timed_scan(ph, op,
                     Rng(seed, ph, op, 64) % std::max<uint64_t>(1, U / 6),
                     scan_profile ? 300 : 120);
        }
        continue;
      }
      uint64_t center = MovingHotCenter(seed, ph, op, U, pf.window);
      uint64_t kid = (Rng(seed, ph, op, 3) % 100 < 80)
                         ? SampleHot(seed, ph, op, center, pf.window, U)
                         : SampleHeavyTail(seed, ph, op, U);
      uint64_t cl = Rng(seed, ph, op, 4) % 100;
      if (cl < 70)
        put(ph, op, kid, PickValueSize(seed, ph, op, mix2));
      else if (cl < 90)
        timed_get(ph, op, kid);
      else
        del(ph, op, kid);
    }
    ops_per_sec[2] =
        double(pf.p2) /
        std::max(1e-6,
                 std::chrono::duration<double>(Clock::now() - t0).count());
    check_background_errors("phase2");
  }
  run_compaction_cycle("phase2");
  if (snapshot_profile) {
    capture_snapshot();
  }
  // Phase 3: tombstone burst.
  {
    uint32_t ph = 3;
    auto t0 = Clock::now();
    for (uint64_t op = 0; op < pf.p3; ++op) {
      uint64_t kid;
      if (Rng(seed, ph, op, 6) % 100 < 70) {
        uint64_t past = Rng(seed, ph, op, 7) % std::max<uint64_t>(1, pf.p2);
        kid = SampleHot(seed, ph, op,
                        MovingHotCenter(seed, 2, past, U, pf.window), pf.window,
                        U);
      } else
        kid = Rng(seed, ph, op, 8) % U;
      uint64_t cl = Rng(seed, ph, op, 5) % 100;
      if (cl < 45) {
        if (Rng(seed, ph, op, 9) % 100 < 90)
          del(ph, op, kid);
        else {
          uint64_t span = range_profile ? 128 + (Rng(seed, ph, op, 11) % 3969)
                                        : 32 + (Rng(seed, ph, op, 11) % 481);
          delrange(ph, op, kid, kid + span);
        }
      } else if (cl < 75)
        put(ph, op, kid, 400);
      else if (cl < 95)
        timed_get(ph, op, kid);
      else
        timed_scan(ph, op, kid, scan_profile ? 400 : 100);
    }
    ops_per_sec[3] =
        double(pf.p3) /
        std::max(1e-6,
                 std::chrono::duration<double>(Clock::now() - t0).count());
    check_background_errors("phase3");
  }
  run_compaction_cycle("phase3");
  // Phase 4: abrupt skew shift.
  {
    uint32_t ph = 4;
    uint64_t new_center = Rng(seed, ph, 0, 50) % U;
    auto t0 = Clock::now();
    for (uint64_t op = 0; op < pf.p4; ++op) {
      if (time_series_profile) {
        uint64_t tail =
            (pf.p0 + pf.p1 + pf.p2 + op * 5 + (Rng(seed, ph, op, 71) % 512)) %
            U;
        uint64_t cl_ts = Rng(seed, ph, op, 72) % 100;
        if (cl_ts < 70) {
          put(ph, op, tail, PickValueSize(seed, ph, op, mix4));
        } else if (cl_ts < 90) {
          timed_get(ph, op,
                    Rng(seed, ph, op, 73) % std::max<uint64_t>(1, U / 5));
        } else {
          timed_scan(ph, op,
                     Rng(seed, ph, op, 74) % std::max<uint64_t>(1, U / 4),
                     scan_profile ? 500 : 160);
        }
        continue;
      }
      uint64_t bucket = Rng(seed, ph, op, 12) % 100, kid;
      if (bucket < 60)
        kid = SampleHot(seed, ph, op, new_center, pf.window, U);
      else if (bucket < 85) {
        uint64_t past = Rng(seed, ph, op, 13) % std::max<uint64_t>(1, pf.p2);
        kid = SampleHot(seed, ph, op,
                        MovingHotCenter(seed, 2, past, U, pf.window), pf.window,
                        U);
      } else
        kid = SampleHeavyTail(seed, ph, op, U);
      uint64_t cl = Rng(seed, ph, op, 14) % 100;
      if (cl < 65)
        put(ph, op, kid, PickValueSize(seed, ph, op, mix4));
      else if (cl < 90)
        timed_get(ph, op, kid);
      else
        timed_scan(ph, op, kid, scan_profile ? 500 : 100);
    }
    ops_per_sec[4] =
        double(pf.p4) /
        std::max(1e-6,
                 std::chrono::duration<double>(Clock::now() - t0).count());
    check_background_errors("phase4");
  }
  verify_snapshot(false);
  check_background_errors("post-phase4");

  flush_memtables("pre-drain");
  const LsmMetrics pre_lsm = collect_paused_lsm("pre-drain");
  const uint64_t pre_drain_table_bytes = table_file_bytes();
  if (pre_lsm.active_memtable_entries != 0 ||
      pre_lsm.immutable_memtables != 0) {
    fail("pre-drain-memtable-not-empty");
  }
  uint64_t live_pre = 0;
  for (const auto& cf_oracle : oracle)
    for (const auto& e : cf_oracle)
      if (e.present) live_pre += 16 + e.size;
  double pre_denom = double(std::max<uint64_t>(live_pre, 64ull << 20));
  double pre_drain_space_amp = double(pre_drain_table_bytes) / pre_denom;
  double pre_drain_get_p99 = percentile_copy(get_lat_us, 0.99);
  double pre_drain_scan_p99 = percentile_copy(scan_lat_us, 0.99);

  // Phase 5: drain + read audit.
  LsmMetrics final_lsm;
  double drain_ms = 0.0;
  const uint64_t drain_compaction_before =
      listener->compaction_output_bytes.load(std::memory_order_relaxed);
  {
    auto drain_t0 = Clock::now();
    run_compaction_cycle("final");
    drain_ms =
        std::chrono::duration<double, std::milli>(Clock::now() - drain_t0)
            .count();
    verify_snapshot(true);
    uint32_t ph = 5;
    uint64_t every = std::max<uint64_t>(1, pf.p5_reads / 20000);
    for (uint64_t i = 0; i < pf.p5_reads; ++i) {
      uint64_t kid = (time_series_profile && (Rng(seed, ph, i, 88) % 100 < 65))
                         ? (Rng(seed, ph, i, 89) % std::max<uint64_t>(1, U / 6))
                         : (Rng(seed, ph, i, 1) % U);
      size_t cf = cf_for(ph, i, kid);
      std::string k = MakeKey(kid, seed), got;
      auto t0 = Clock::now();
      rocksdb::Status st = db->Get(ro, cf_handles[cf], k, &got);
      get_lat_us.push_back(
          std::chrono::duration<double, std::micro>(Clock::now() - t0).count());
      if (i % every == 0) {
        auto& e = oracle[cf][kid];
        if (e.present) {
          auto h = Hash128(got);
          if (!st.ok() || got.size() != e.size || h.first != e.h1 ||
              h.second != e.h2) {
            fail("get-mismatch present");
          }
        } else if (!st.IsNotFound()) {
          fail("get-mismatch deleted");
        }
      } else if (!st.ok() && !st.IsNotFound()) {
        fail("get-audit: " + st.ToString());
      }
    }
    for (uint64_t i = 0; i < pf.p5_scans; ++i) {
      uint64_t start =
          (time_series_profile && (Rng(seed, ph, i, 90) % 100 < 70))
              ? (Rng(seed, ph, i, 91) % std::max<uint64_t>(1, U / 5))
              : (Rng(seed, ph, i, 2) % U);
      timed_scan(ph, i, start, scan_profile ? 500 : 100);
    }
  }
  final_lsm = collect_paused_lsm("final");
  const uint64_t drain_compaction_bytes =
      listener->compaction_output_bytes.load(std::memory_order_relaxed) -
      drain_compaction_before;

  uint64_t flush_bytes = listener->flush_output_bytes.load();
  uint64_t comp_bytes = listener->compaction_output_bytes.load();
  uint64_t table_bytes = listener->table_created_bytes.load();
  uint64_t read_amp_useful = options.statistics->getTickerCount(
      rocksdb::READ_AMP_ESTIMATE_USEFUL_BYTES);
  uint64_t read_amp_total =
      options.statistics->getTickerCount(rocksdb::READ_AMP_TOTAL_READ_BYTES);
  double read_amp =
      double(read_amp_total) / double(std::max<uint64_t>(1, read_amp_useful));
  uint64_t stall_micros =
      options.statistics->getTickerCount(rocksdb::STALL_MICROS);

  uint64_t oracle_count = 0, oracle_size_sum = 0;
  for (size_t cf = 0; cf < oracle.size(); ++cf) {
    for (uint64_t id = 0; id < U; ++id) {
      const auto& e = oracle[cf][id];
      if (!e.present) continue;
      ++oracle_count;
      oracle_size_sum += e.size;
    }
  }

  // Reopen + full iterator check against the exact oracle entry for each key.
  if (held_snapshot) {
    db->ReleaseSnapshot(held_snapshot);
    held_snapshot = nullptr;
  }
  for (auto* h : owned_cf_handles) db->DestroyColumnFamilyHandle(h);
  owned_cf_handles.clear();
#if ROCKSDB_VERSION_GE(11, 0, 0)
  db_owner.reset();
#else
  delete db;
  db = nullptr;
#endif
  db = nullptr;
  rocksdb::Options ropts = MakeOptions(pf, nullptr);
  std::vector<rocksdb::ColumnFamilyHandle*> reopen_handles;
  rocksdb::Status rs;
#if ROCKSDB_VERSION_GE(11, 0, 0)
  std::unique_ptr<rocksdb::DB> reopen_owner;
#endif
  if (pf.num_cfs > 1) {
    std::vector<rocksdb::ColumnFamilyDescriptor> descs;
    descs.emplace_back(rocksdb::kDefaultColumnFamilyName,
                       rocksdb::ColumnFamilyOptions(ropts));
    for (int i = 1; i < pf.num_cfs; ++i)
      descs.emplace_back("cf" + std::to_string(i),
                         rocksdb::ColumnFamilyOptions(ropts));
#if ROCKSDB_VERSION_GE(11, 0, 0)
    rs = rocksdb::DB::Open(rocksdb::DBOptions(ropts), db_dir, descs,
                           &reopen_handles, &reopen_owner);
    db = reopen_owner.get();
#else
    rs = rocksdb::DB::Open(rocksdb::DBOptions(ropts), db_dir, descs,
                           &reopen_handles, &db);
#endif
  } else {
#if ROCKSDB_VERSION_GE(11, 0, 0)
    rs = rocksdb::DB::Open(ropts, db_dir, &reopen_owner);
    db = reopen_owner.get();
#else
    rs = rocksdb::DB::Open(ropts, db_dir, &db);
#endif
    if (rs.ok()) reopen_handles.push_back(db->DefaultColumnFamily());
  }
  if (!rs.ok()) {
    fail("reopen: " + rs.ToString());
  } else {
    uint64_t db_count = 0, db_size_sum = 0;
    std::vector<std::vector<uint8_t>> seen(oracle.size(),
                                           std::vector<uint8_t>(U, uint8_t{0}));
    for (size_t cf = 0; cf < reopen_handles.size(); ++cf) {
      if (cf >= oracle.size()) {
        fail("iterator unexpected column family");
        break;
      }
      std::unique_ptr<rocksdb::Iterator> it(
          db->NewIterator(ro, reopen_handles[cf]));
      for (it->SeekToFirst(); it->Valid(); it->Next()) {
        uint64_t id = KeyIdFromSlice(it->key().data(), it->key().size());
        if (id >= U) {
          fail("iterator unexpected key id");
          continue;
        }
        std::string expected_key = MakeKey(id, seed);
        if (it->key().compare(rocksdb::Slice(expected_key)) != 0) {
          fail("iterator key mismatch");
          continue;
        }
        const auto& e = oracle[cf][id];
        if (!e.present) {
          fail("iterator unexpected live key");
          continue;
        }
        if (seen[cf][id]) {
          fail("iterator duplicate key");
          continue;
        }
        auto v = it->value();
        auto h = Hash128(v.data(), v.size());
        if (v.size() != e.size || h.first != e.h1 || h.second != e.h2) {
          fail("iterator value mismatch");
          continue;
        }
        seen[cf][id] = 1;
        ++db_count;
        db_size_sum += uint32_t(v.size());
      }
      if (!it->status().ok()) {
        fail("iter status: " + it->status().ToString());
      }
    }
    for (size_t cf = 0; cf < oracle.size(); ++cf) {
      for (uint64_t id = 0; id < U; ++id) {
        if (oracle[cf][id].present && !seen[cf][id]) {
          fail("iterator missing live key");
          break;
        }
      }
    }
    if (db_count != oracle_count || db_size_sum != oracle_size_sum) {
      fail("full-iterator mismatch (count " + std::to_string(db_count) + "/" +
           std::to_string(oracle_count) + ")");
    }
  }
  if (db && pf.num_cfs > 1) {
    for (auto* h : reopen_handles) db->DestroyColumnFamilyHandle(h);
  }
#if ROCKSDB_VERSION_GE(11, 0, 0)
  reopen_owner.reset();
#else
  if (db) delete db;
#endif

  uint64_t live_final = 0;
  for (const auto& cf_oracle : oracle)
    for (const auto& e : cf_oracle)
      if (e.present) live_final += 16 + e.size;
  double denom = double(std::max<uint64_t>(live_final, 64ull << 20));
  const uint64_t final_table_bytes = table_file_bytes();
  double final_space_amp = double(final_table_bytes) / denom;
  double lsm_waf =
      double(table_bytes) / double(std::max<uint64_t>(1, user_put_bytes));

  std::ofstream o(out_path);
  o.setf(std::ios::fixed);
  o << "{\n  \"ok\": true,\n";
  o << "  \"correctness_ok\": " << (correctness_ok ? "true" : "false") << ",\n";
  o << "  \"fail_reason\": \"" << JsonEscape(fail_reason) << "\",\n";
  o << "  \"phase1_ops_per_sec\": " << ops_per_sec[1] << ",\n";
  o << "  \"phase2_ops_per_sec\": " << ops_per_sec[2] << ",\n";
  o << "  \"phase3_ops_per_sec\": " << ops_per_sec[3] << ",\n";
  o << "  \"phase4_ops_per_sec\": " << ops_per_sec[4] << ",\n";
  o << "  \"lsm_waf\": " << lsm_waf << ",\n";
  o << "  \"get_p99_us\": " << Percentile(get_lat_us, 0.99) << ",\n";
  o << "  \"scan_p99_us\": " << Percentile(scan_lat_us, 0.99) << ",\n";
  o << "  \"pre_drain_get_p99_us\": " << pre_drain_get_p99 << ",\n";
  o << "  \"pre_drain_scan_p99_us\": " << pre_drain_scan_p99 << ",\n";
  o << "  \"pre_drain_space_amp\": " << pre_drain_space_amp << ",\n";
  o << "  \"pre_drain_lsm_bytes\": " << pre_drain_table_bytes << ",\n";
  o << "  \"pre_drain_l0_base_overlap_bytes\": "
    << pre_lsm.l0_base_overlap_bytes << ",\n";
  o << "  \"pre_drain_pending_compaction_bytes\": " << pre_lsm.pending << ",\n";
  o << "  \"pre_drain_l0_files\": " << pre_lsm.level_files[0] << ",\n";
  o << "  \"pre_drain_l0_files_by_cf\": [";
  for (size_t i = 0; i < pre_lsm.l0_files_by_cf.size(); ++i) {
    if (i > 0) o << ",";
    o << pre_lsm.l0_files_by_cf[i];
  }
  o << "],\n";
  o << "  \"pre_drain_level_files\": [" << pre_lsm.level_files[0] << ","
    << pre_lsm.level_files[1] << "," << pre_lsm.level_files[2] << ","
    << pre_lsm.level_files[3] << "," << pre_lsm.level_files[4] << ","
    << pre_lsm.level_files[5] << "],\n";
  o << "  \"pre_drain_level_bytes\": [" << pre_lsm.level_bytes[0] << ","
    << pre_lsm.level_bytes[1] << "," << pre_lsm.level_bytes[2] << ","
    << pre_lsm.level_bytes[3] << "," << pre_lsm.level_bytes[4] << ","
    << pre_lsm.level_bytes[5] << "],\n";
  o << "  \"drain_ms\": " << drain_ms << ",\n";
  o << "  \"drain_compaction_bytes\": " << drain_compaction_bytes << ",\n";
  o << "  \"final_space_amp\": " << final_space_amp << ",\n";
  o << "  \"final_lsm_bytes\": " << final_table_bytes << ",\n";
  o << "  \"pending_compaction_bytes\": " << final_lsm.pending << ",\n";
  o << "  \"l0_files\": " << final_lsm.level_files[0] << ",\n";
  o << "  \"level_files\": [" << final_lsm.level_files[0] << ","
    << final_lsm.level_files[1] << "," << final_lsm.level_files[2] << ","
    << final_lsm.level_files[3] << "," << final_lsm.level_files[4] << ","
    << final_lsm.level_files[5] << "],\n";
  o << "  \"column_families\": " << final_lsm.column_families << ",\n";
  o << "  \"base_fingerprint\": " << base_fingerprint << ",\n";
  o << "  \"l0_trigger\": " << pf.l0_trigger << ",\n";
  o << "  \"compaction_events\": " << listener->compaction_events.load()
    << ",\n";
  o << "  \"intra_l0_compactions\": " << listener->intra_l0_compactions.load()
    << ",\n";
  o << "  \"failed_compactions\": " << listener->failed_compactions.load()
    << ",\n";
  o << "  \"background_errors\": " << listener->background_errors.load()
    << ",\n";
  o << "  \"user_put_bytes\": " << user_put_bytes << ",\n";
  o << "  \"live_logical_bytes\": " << live_final << ",\n";
  o << "  \"flush_output_bytes\": " << flush_bytes << ",\n";
  o << "  \"compaction_output_bytes\": " << comp_bytes << ",\n";
  o << "  \"table_created_bytes\": " << table_bytes << ",\n";
  o << "  \"read_amp\": " << read_amp << ",\n";
  o << "  \"stall_micros\": " << stall_micros << "\n}\n";
  o.close();

  return 0;
}
