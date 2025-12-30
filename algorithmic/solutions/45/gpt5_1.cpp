#include <bits/stdc++.h>
using namespace std;

// Fast input
struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char getChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return EOF;
        }
        return buf[idx++];
    }
    bool readInt(int &out) {
        char c;
        int sgn = 1;
        int x = 0;
        c = getChar();
        if (c == EOF) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (c == EOF) return false;
        }
        if (c == '-') { sgn = -1; c = getChar(); }
        for (; c >= '0' && c <= '9'; c = getChar()) x = x * 10 + (c - '0');
        out = x * sgn;
        return true;
    }
    bool readLL(long long &out) {
        char c;
        int sgn = 1;
        long long x = 0;
        c = getChar();
        if (c == EOF) return false;
        while (c != '-' && (c < '0' || c > '9')) {
            c = getChar();
            if (c == EOF) return false;
        }
        if (c == '-') { sgn = -1; c = getChar(); }
        for (; c >= '0' && c <= '9'; c = getChar()) x = x * 10 + (c - '0');
        out = x * sgn;
        return true;
    }
    bool readDouble(double &out) {
        char c = getChar();
        if (c == EOF) return false;
        while (c != '-' && c != '.' && (c < '0' || c > '9')) {
            c = getChar();
            if (c == EOF) return false;
        }
        int sgn = 1;
        if (c == '-') { sgn = -1; c = getChar(); }
        long long ip = 0;
        while (c >= '0' && c <= '9') {
            ip = ip * 10 + (c - '0');
            c = getChar();
        }
        double fp = 0.0, base = 0.1;
        if (c == '.') {
            c = getChar();
            while (c >= '0' && c <= '9') {
                fp += (c - '0') * base;
                base *= 0.1;
                c = getChar();
            }
        }
        out = sgn * (double(ip) + fp);
        return true;
    }
};

// Fast output
struct FastOutput {
    static const int BUFSIZE = 1 << 20;
    int idx;
    char buf[BUFSIZE];
    FastOutput() : idx(0) {}
    ~FastOutput() { flush(); }
    inline void pushChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }
    inline void writeInt(int x) {
        if (x == 0) {
            pushChar('0');
            return;
        }
        if (x < 0) {
            pushChar('-');
            x = -x;
        }
        char s[16]; int n = 0;
        while (x) { s[n++] = char('0' + (x % 10)); x /= 10; }
        while (n--) pushChar(s[n]);
    }
    inline void writeSpace() { pushChar(' '); }
    inline void writeNewline() { pushChar('\n'); }
    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }
};

// RNG
static uint64_t splitmix64_state = 0x9e3779b97f4a7c15ULL;
static inline uint64_t splitmix64() {
    uint64_t z = (splitmix64_state += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}
template <class It>
inline void rng_shuffle(It first, It last) {
    // Fisher-Yates
    if (first == last) return;
    size_t n = (size_t)(last - first);
    for (size_t i = n - 1; i > 0; --i) {
        size_t j = (size_t)(splitmix64() % (i + 1));
        if (i != j) swap(first[i], first[j]);
    }
}

struct Edge { int u, v; };

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    FastOutput fo;

    int n, k;
    long long m;
    double eps;
    if (!fs.readInt(n)) return 0;
    fs.readLL(m);
    fs.readInt(k);
    fs.readDouble(eps);

    vector<Edge> edges;
    edges.reserve((size_t)min<long long>(m, 20000000LL));
    vector<int> deg(n + 1, 0);

    // Read edges, ignore self-loops
    for (long long i = 0; i < m; ++i) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        if (u == v) continue;
        edges.push_back({u, v});
        deg[u]++; deg[v]++;
    }

    // Build adjacency (CSR-like)
    vector<int> offset(n + 2, 0);
    for (int v = 1; v <= n; ++v) offset[v + 1] = offset[v] + deg[v];
    vector<int> adj;
    adj.resize((size_t)offset[n + 1]);
    vector<int> cur(n + 1, 0);
    for (int v = 1; v <= n; ++v) cur[v] = offset[v];
    for (const auto &e : edges) {
        adj[cur[e.u]++] = e.v;
        adj[cur[e.v]++] = e.u;
    }
    // Free edges
    edges.clear();
    edges.shrink_to_fit();

    // Seeds: pick up to k highest-degree vertices
    struct Pair { int d, v; };
    struct Cmp { bool operator()(const Pair &a, const Pair &b) const {
        if (a.d != b.d) return a.d > b.d; // min-heap by degree
        return a.v > b.v;
    } };
    priority_queue<Pair, vector<Pair>, Cmp> pq;
    for (int v = 1; v <= n; ++v) {
        int d = offset[v + 1] - offset[v];
        if ((int)pq.size() < k) pq.push({d, v});
        else if (d > pq.top().d) {
            pq.pop();
            pq.push({d, v});
        }
    }
    vector<int> seeds;
    seeds.reserve(k);
    vector<char> isSeed(n + 1, 0);
    while (!pq.empty()) {
        seeds.push_back(pq.top().v);
        isSeed[pq.top().v] = 1;
        pq.pop();
    }
    // If fewer than k seeds, fill with random vertices
    if ((int)seeds.size() < k) {
        for (int v = 1; v <= n && (int)seeds.size() < k; ++v) {
            if (!isSeed[v]) {
                seeds.push_back(v);
                isSeed[v] = 1;
            }
        }
    }

    // Partition parameters
    long long ideal_ll = (n + (long long)k - 1) / (long long)k; // ceil(n/k)
    int ideal = (int)ideal_ll;
    int cap = (int)floor((1.0 + eps) * (double)ideal + 1e-9);
    if (cap < 1) cap = 1;

    vector<int> part(n + 1, -1);
    vector<int> load(k, 0);

    // Assign seeds to distinct parts 0..k-1 (wrap if more seeds than k, shouldn't happen)
    for (int i = 0; i < (int)seeds.size() && i < k; ++i) {
        int s = seeds[i];
        if (part[s] == -1) {
            part[s] = i;
            load[i]++;
        }
    }

    // Random order for assignment
    splitmix64_state = chrono::steady_clock::now().time_since_epoch().count();
    vector<int> order(n);
    for (int i = 0; i < n; ++i) order[i] = i + 1;
    rng_shuffle(order.begin(), order.end());

    // Helper arrays for neighbor part counts
    vector<int> cntK(k, 0);
    vector<int> usedParts;
    usedParts.reserve(64);

    auto time_start = chrono::steady_clock::now();
    auto elapsed_ms = [&]() -> double {
        auto now = chrono::steady_clock::now();
        return chrono::duration<double, std::milli>(now - time_start).count();
    };

    // Initial assignment with LDG-style heuristic: prefer parts with many neighbors, tie-break by low load
    for (int idx = 0; idx < n; ++idx) {
        int v = order[idx];
        if (part[v] != -1) continue;

        usedParts.clear();
        int st = offset[v], en = offset[v + 1];
        for (int it = st; it < en; ++it) {
            int u = adj[it];
            int q = part[u];
            if (q >= 0) {
                if (cntK[q] == 0) usedParts.push_back(q);
                cntK[q]++;
            }
        }
        int bestPart = -1;
        int bestCount = -1;
        int bestLoad = INT_MAX;

        // Among encountered parts with capacity, pick max count, then min load
        for (int q : usedParts) {
            if (load[q] < cap) {
                int c = cntK[q];
                if (c > bestCount || (c == bestCount && load[q] < bestLoad)) {
                    bestCount = c;
                    bestLoad = load[q];
                    bestPart = q;
                }
            }
        }
        // Fallback: pick least loaded part with capacity
        if (bestPart == -1) {
            int minLoad = INT_MAX, arg = -1;
            for (int j = 0; j < k; ++j) {
                if (load[j] < cap && load[j] < minLoad) {
                    minLoad = load[j];
                    arg = j;
                }
            }
            if (arg == -1) {
                // Should not happen; pick any with space by scanning again
                for (int j = 0; j < k; ++j) if (load[j] < cap) { arg = j; break; }
                if (arg == -1) arg = 0; // fallback, but may violate; extremely unlikely
            }
            bestPart = arg;
        }
        part[v] = bestPart;
        load[bestPart]++;

        // reset counts
        for (int q : usedParts) cntK[q] = 0;
    }

    // Refinement passes (label propagation-like)
    int max_passes = 2;
    for (int pass = 0; pass < max_passes; ++pass) {
        if (elapsed_ms() > 900.0) break;
        rng_shuffle(order.begin(), order.end());
        int moves = 0;
        for (int idx = 0; idx < n; ++idx) {
            int v = order[idx];
            int curp = part[v];
            usedParts.clear();
            int st = offset[v], en = offset[v + 1];
            for (int it = st; it < en; ++it) {
                int u = adj[it];
                int q = part[u];
                if (q >= 0) {
                    if (cntK[q] == 0) usedParts.push_back(q);
                    cntK[q]++;
                }
            }
            int curCount = 0;
            if (curp >= 0 && cntK[curp] > 0) curCount = cntK[curp];
            int bestp = curp;
            int bestc = curCount;

            // choose neighbor part improving count
            for (int q : usedParts) {
                if (q == curp) continue;
                if (load[q] < cap) {
                    int c = cntK[q];
                    if (c > bestc) {
                        bestc = c;
                        bestp = q;
                    }
                }
            }
            if (bestp != curp) {
                part[v] = bestp;
                load[curp]--;
                load[bestp]++;
                moves++;
            }
            for (int q : usedParts) cntK[q] = 0;
        }
        if (moves == 0) break;
    }

    // Ensure no part exceeds cap (safety fallback - should already hold)
    // If any overload exists, move some vertices to underloaded parts arbitrarily
    // This loop is rarely executed; but keep it light
    vector<int> under;
    vector<int> over;
    for (int j = 0; j < k; ++j) {
        if (load[j] < cap) under.push_back(j);
        else if (load[j] > cap) over.push_back(j);
    }
    if (!over.empty()) {
        // gather vertices in overloaded parts
        vector<int> cand;
        cand.reserve(n / 10 + 1);
        for (int v = 1; v <= n; ++v) {
            if (part[v] >= 0 && load[part[v]] > cap) cand.push_back(v);
        }
        for (int v : cand) {
            int pcur = part[v];
            if (load[pcur] <= cap) continue;
            int bestj = -1;
            int minLoad = INT_MAX;
            for (int j = 0; j < k; ++j) {
                if (load[j] < cap) {
                    if (load[j] < minLoad) {
                        minLoad = load[j];
                        bestj = j;
                    }
                }
            }
            if (bestj != -1) {
                part[v] = bestj;
                load[bestj]++;
                load[pcur]--;
            }
        }
    }

    // Output partition (1-based labels)
    for (int v = 1; v <= n; ++v) {
        int lab = part[v];
        if (lab < 0) {
            // If any unassigned (shouldn't happen), assign to a random part with space
            int j = (int)(splitmix64() % k);
            int tries = 0;
            while (tries < k && load[j] >= cap) { j = (j + 1) & (k - 1); tries++; }
            lab = j;
            part[v] = lab;
            load[lab]++;
        }
        fo.writeInt(lab + 1);
        if (v < n) fo.writeSpace();
    }
    fo.writeNewline();
    fo.flush();
    return 0;
}