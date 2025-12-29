#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 22;
    char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline char read() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    inline bool readInt(int &out) {
        char c;
        do {
            c = read();
            if (!c) return false;
        } while (c <= ' ');

        int sgn = 1;
        if (c == '-') {
            sgn = -1;
            c = read();
        }
        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = read();
        }
        out = x * sgn;
        return true;
    }
};

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed) : x(seed) {}
    inline uint64_t nextU64() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    inline uint32_t nextU32() { return (uint32_t)nextU64(); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    vector<int> lit;
    lit.resize((size_t)m * 3);

    vector<int> cnt(n + 1, 0);

    for (int i = 0; i < m; i++) {
        int a, b, c;
        fs.readInt(a); fs.readInt(b); fs.readInt(c);
        lit[(size_t)i * 3 + 0] = a;
        lit[(size_t)i * 3 + 1] = b;
        lit[(size_t)i * 3 + 2] = c;
        cnt[abs(a)]++;
        cnt[abs(b)]++;
        cnt[abs(c)]++;
    }

    vector<uint32_t> off(n + 2, 0);
    for (int v = 1; v <= n; v++) off[v + 1] = off[v] + (uint32_t)cnt[v];
    const uint32_t totalOcc = off[n + 1];

    vector<uint32_t> occClause(totalOcc);
    vector<uint8_t> occWant(totalOcc);
    vector<uint32_t> cur = off;

    for (uint32_t i = 0; i < (uint32_t)m; i++) {
        int a = lit[(size_t)i * 3 + 0];
        int b = lit[(size_t)i * 3 + 1];
        int c = lit[(size_t)i * 3 + 2];

        auto addOcc = [&](int x) {
            uint32_t v = (uint32_t)abs(x);
            uint8_t want = (x > 0) ? 1 : 0;
            uint32_t p = cur[v]++;
            occClause[p] = i;
            occWant[p] = want;
        };
        addOcc(a);
        addOcc(b);
        addOcc(c);
    }

    uint64_t seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    seed ^= (uint64_t)(uintptr_t)&seed;
    SplitMix64 rng(seed);

    vector<uint8_t> bestVal(n + 1, 0);
    int bestSat = -1;

    if (m == 0) {
        // Any assignment yields score 1
        for (int i = 1; i <= n; i++) bestVal[i] = (uint8_t)(rng.nextU32() & 1u);
        string out;
        out.reserve((size_t)n * 2 + 2);
        for (int i = 1; i <= n; i++) {
            out.push_back(char('0' + bestVal[i]));
            out.push_back(i == n ? '\n' : ' ');
        }
        fwrite(out.data(), 1, out.size(), stdout);
        return 0;
    }

    int passes = (m > 1500000 ? 4 : 6);
    int restarts = 1;
    if (m <= 1000000) restarts = 2;
    if (m <= 300000) restarts = 3;

    vector<uint8_t> val(n + 1, 0);
    vector<uint8_t> satCount(m, 0);

    // For handling duplicate literals per variable within a clause efficiently/correctly
    vector<int> mark(m, 0);
    vector<uint8_t> kCount(m, 0), tTrue(m, 0);
    int iterId = 1;

    vector<int> order(n);
    for (int i = 0; i < n; i++) order[i] = i + 1;

    int maxOccVar = 0;
    for (int v = 1; v <= n; v++) maxOccVar = max(maxOccVar, cnt[v]);
    size_t reserveSize = min<size_t>((size_t)maxOccVar, 1000000);
    vector<int> touched;
    vector<int8_t> netChange;
    touched.reserve(reserveSize);
    netChange.reserve(reserveSize);

    auto computeSatCount = [&]() -> int {
        int satisfied = 0;
        for (int i = 0; i < m; i++) {
            int a = lit[(size_t)i * 3 + 0];
            int b = lit[(size_t)i * 3 + 1];
            int c = lit[(size_t)i * 3 + 2];
            uint32_t va = (uint32_t)abs(a);
            uint32_t vb = (uint32_t)abs(b);
            uint32_t vc = (uint32_t)abs(c);
            uint8_t ta = (uint8_t)(val[va] ^ (uint8_t)(a < 0));
            uint8_t tb = (uint8_t)(val[vb] ^ (uint8_t)(b < 0));
            uint8_t tc = (uint8_t)(val[vc] ^ (uint8_t)(c < 0));
            uint8_t sc = (uint8_t)(ta + tb + tc);
            satCount[i] = sc;
            satisfied += (sc != 0);
        }
        return satisfied;
    };

    auto greedyImprove = [&](int &satisfied) {
        for (int pass = 0; pass < passes; pass++) {
            // shuffle variable order
            for (int i = n - 1; i > 0; i--) {
                int j = (int)(rng.nextU32() % (uint32_t)(i + 1));
                swap(order[i], order[j]);
            }

            bool improved = false;

            for (int idxVar = 0; idxVar < n; idxVar++) {
                int v = order[idxVar];
                if (cnt[v] == 0) continue;

                touched.clear();
                netChange.clear();
                int myIter = iterId++;
                if (iterId == INT_MAX) {
                    fill(mark.begin(), mark.end(), 0);
                    iterId = 1;
                }

                uint8_t vv = val[v];
                uint32_t l = off[v], r = off[v + 1];
                for (uint32_t p = l; p < r; p++) {
                    int ci = (int)occClause[p];
                    if (mark[ci] != myIter) {
                        mark[ci] = myIter;
                        touched.push_back(ci);
                        kCount[ci] = 0;
                        tTrue[ci] = 0;
                    }
                    kCount[ci]++;
                    tTrue[ci] += (uint8_t)(vv == occWant[p]);
                }

                int delta = 0;
                netChange.reserve(touched.size());
                for (int ci : touched) {
                    int8_t net = (int8_t)((int)kCount[ci] - 2 * (int)tTrue[ci]);
                    netChange.push_back(net);
                    uint8_t oldSat = satCount[ci];
                    int newSat = (int)oldSat + (int)net;
                    if (oldSat == 0 && newSat > 0) delta++;
                    else if (oldSat > 0 && newSat == 0) delta--;
                }

                if (delta > 0) {
                    // apply flip
                    for (size_t ti = 0; ti < touched.size(); ti++) {
                        int ci = touched[ti];
                        int net = (int)netChange[ti];
                        uint8_t oldSat = satCount[ci];
                        int newSat = (int)oldSat + net;
                        satCount[ci] = (uint8_t)newSat;
                        if (oldSat == 0 && newSat > 0) satisfied++;
                        else if (oldSat > 0 && newSat == 0) satisfied--;
                    }
                    val[v] ^= 1;
                    improved = true;
                }
            }

            if (!improved) break;
        }
    };

    for (int r = 0; r < restarts; r++) {
        for (int v = 1; v <= n; v++) val[v] = (uint8_t)(rng.nextU32() & 1u);

        int satisfied = computeSatCount();
        greedyImprove(satisfied);

        if (satisfied > bestSat) {
            bestSat = satisfied;
            bestVal = val;
            if (bestSat == m) break;
        }
    }

    string out;
    out.reserve((size_t)n * 2 + 2);
    for (int i = 1; i <= n; i++) {
        out.push_back(char('0' + bestVal[i]));
        out.push_back(i == n ? '\n' : ' ');
    }
    fwrite(out.data(), 1, out.size(), stdout);
    return 0;
}