#include <bits/stdc++.h>
using namespace std;

class FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    unsigned char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline bool refill() {
        size = fread(buf, 1, BUFSIZE, stdin);
        idx = 0;
        return size > 0;
    }

public:
    inline bool skipBlanks() {
        while (true) {
            if (idx >= size) {
                if (!refill()) return false;
            }
            if (buf[idx] > ' ') return true;
            idx++;
        }
    }

    template <class T>
    bool readInt(T &out) {
        if (!skipBlanks()) return false;
        bool neg = false;
        if (buf[idx] == '-') { neg = true; idx++; }
        T val = 0;
        while (true) {
            if (idx >= size) {
                if (!refill()) break;
            }
            unsigned char c = buf[idx];
            if (c < '0' || c > '9') break;
            val = val * 10 + (c - '0');
            idx++;
        }
        out = neg ? -val : val;
        return true;
    }

    bool readDouble(double &out) {
        if (!skipBlanks()) return false;
        bool neg = false;
        if (buf[idx] == '-') { neg = true; idx++; }
        long double val = 0;
        while (true) {
            if (idx >= size) {
                if (!refill()) break;
            }
            unsigned char c = buf[idx];
            if (c < '0' || c > '9') break;
            val = val * 10 + (c - '0');
            idx++;
        }
        long double frac = 0, base = 1;
        if (idx < size || refill()) {
            if (idx < size && buf[idx] == '.') {
                idx++;
                while (true) {
                    if (idx >= size) {
                        if (!refill()) break;
                    }
                    unsigned char c = buf[idx];
                    if (c < '0' || c > '9') break;
                    base *= 10;
                    frac = frac * 10 + (c - '0');
                    idx++;
                }
            }
        }
        val += frac / base;
        out = (double)(neg ? -val : val);
        return true;
    }
};

class FastOutput {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0;

public:
    ~FastOutput() { flush(); }

    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }

    inline void pushChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }

    inline void writeInt(int x, char after) {
        if (x == 0) {
            pushChar('0');
            if (after) pushChar(after);
            return;
        }
        char s[16];
        int n = 0;
        while (x > 0) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        while (n--) pushChar(s[n]);
        if (after) pushChar(after);
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;

    int n, m;
    int k;
    double eps;
    if (!fs.readInt(n)) return 0;
    if (!fs.readInt(m)) return 0;
    if (!fs.readInt(k)) return 0;
    if (!fs.readDouble(eps)) return 0;

    vector<uint32_t> deg((size_t)n, 0);
    vector<uint32_t> eu;
    vector<uint32_t> ev;
    eu.reserve((size_t)m);
    ev.reserve((size_t)m);

    for (int i = 0; i < m; i++) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        if (u == v) continue;
        u--; v--;
        if ((unsigned)u >= (unsigned)n || (unsigned)v >= (unsigned)n) continue;
        eu.push_back((uint32_t)u);
        ev.push_back((uint32_t)v);
        deg[(size_t)u]++;
        deg[(size_t)v]++;
    }

    size_t m2 = eu.size();
    vector<uint64_t> off((size_t)n + 1, 0);
    for (int i = 0; i < n; i++) off[(size_t)i + 1] = off[(size_t)i] + deg[(size_t)i];
    vector<uint32_t> adj(off.back());
    vector<uint64_t> cur = off;
    for (size_t i = 0; i < m2; i++) {
        uint32_t u = eu[i], v = ev[i];
        adj[cur[u]++] = v;
        adj[cur[v]++] = u;
    }
    vector<uint32_t>().swap(eu);
    vector<uint32_t>().swap(ev);

    long long ideal = ( (long long)n + (long long)k - 1 ) / (long long)k;
    long double cap_ld = floor((1.0L + (long double)eps) * (long double)ideal + 1e-15L);
    long long cap = (long long)cap_ld;
    if (cap < 1) cap = 1;

    int kk = k;
    vector<int> part((size_t)n, 0);
    vector<int> sz((size_t)kk + 1, 0);

    // pick top-k degree vertices as seeds
    vector<int> seeds;
    seeds.reserve((size_t)min(kk, n));
    if (kk <= n) {
        using P = pair<uint32_t, int>;
        priority_queue<P, vector<P>, greater<P>> pq;
        pq = priority_queue<P, vector<P>, greater<P>>();
        for (int v = 0; v < n; v++) {
            if ((int)pq.size() < kk) pq.push({deg[(size_t)v], v});
            else if (deg[(size_t)v] > pq.top().first) {
                pq.pop();
                pq.push({deg[(size_t)v], v});
            }
        }
        seeds.resize((size_t)kk);
        for (int i = kk - 1; i >= 0; i--) {
            seeds[(size_t)i] = pq.top().second;
            pq.pop();
        }
        // unique-ify if duplicates (shouldn't) and ensure not repeated; fallback fill if needed
        sort(seeds.begin(), seeds.end());
        seeds.erase(unique(seeds.begin(), seeds.end()), seeds.end());
    } else {
        seeds.resize((size_t)n);
        iota(seeds.begin(), seeds.end(), 0);
    }

    // If fewer than k seeds due to uniqueness (rare), fill with remaining vertices
    if ((int)seeds.size() < min(kk, n)) {
        vector<char> used((size_t)n, 0);
        for (int v : seeds) used[(size_t)v] = 1;
        for (int v = 0; v < n && (int)seeds.size() < min(kk, n); v++) {
            if (!used[(size_t)v]) seeds.push_back(v);
        }
    }

    // BFS growth from seeds
    vector<uint32_t> q;
    q.reserve((size_t)n);

    int seedCount = min((int)seeds.size(), kk);
    for (int i = 0; i < seedCount; i++) {
        int v = seeds[(size_t)i];
        int p = i + 1;
        part[(size_t)v] = p;
        sz[(size_t)p]++;
        q.push_back((uint32_t)v);
    }

    for (size_t qi = 0; qi < q.size(); qi++) {
        uint32_t v = q[qi];
        int p = part[(size_t)v];
        uint64_t l = off[(size_t)v], r = off[(size_t)v + 1];
        for (uint64_t e = l; e < r; e++) {
            uint32_t u = adj[e];
            if (part[(size_t)u] == 0 && sz[(size_t)p] < cap) {
                part[(size_t)u] = p;
                sz[(size_t)p]++;
                q.push_back(u);
            }
        }
    }
    vector<uint32_t>().swap(q);

    // Priority queue for least-loaded part (for leftover assignment)
    using PP = pair<int,int>;
    priority_queue<PP, vector<PP>, greater<PP>> loadpq;
    for (int p = 1; p <= kk; p++) loadpq.push({sz[(size_t)p], p});
    auto getLeastPart = [&]() -> int {
        while (!loadpq.empty()) {
            auto [s, p] = loadpq.top();
            if (s != sz[(size_t)p] || s >= cap) { loadpq.pop(); continue; }
            return p;
        }
        // Shouldn't happen unless cap too small; fallback:
        int best = 1;
        for (int p = 2; p <= kk; p++) if (sz[(size_t)p] < sz[(size_t)best]) best = p;
        return best;
    };

    vector<int> seen((size_t)kk + 1, 0);
    vector<int> cnt((size_t)kk + 1, 0);
    vector<int> plist;
    plist.reserve(64);
    int stamp = 1;

    // Assign remaining vertices by neighbor-majority with capacity
    for (int v = 0; v < n; v++) {
        if (part[(size_t)v] != 0) continue;
        stamp++;
        plist.clear();
        uint64_t l = off[(size_t)v], r = off[(size_t)v + 1];
        for (uint64_t e = l; e < r; e++) {
            int p = part[(size_t)adj[e]];
            if (p == 0) continue;
            if (seen[(size_t)p] != stamp) {
                seen[(size_t)p] = stamp;
                cnt[(size_t)p] = 1;
                plist.push_back(p);
            } else {
                cnt[(size_t)p]++;
            }
        }

        int bestp = 0;
        int bestc = -1;
        int bestsz = INT_MAX;
        for (int p : plist) {
            if (sz[(size_t)p] >= cap) continue;
            int c = cnt[(size_t)p];
            int s = sz[(size_t)p];
            if (c > bestc || (c == bestc && s < bestsz)) {
                bestc = c;
                bestsz = s;
                bestp = p;
            }
        }
        if (bestp == 0) bestp = getLeastPart();

        part[(size_t)v] = bestp;
        sz[(size_t)bestp]++;
        loadpq.push({sz[(size_t)bestp], bestp});
    }

    // Local improvement (label propagation to reduce cut), 2 passes
    for (int pass = 0; pass < 2; pass++) {
        if (pass == 0) {
            for (int v = 0; v < n; v++) {
                int p0 = part[(size_t)v];
                stamp++;
                plist.clear();
                uint64_t l = off[(size_t)v], r = off[(size_t)v + 1];
                for (uint64_t e = l; e < r; e++) {
                    int p = part[(size_t)adj[e]];
                    if (seen[(size_t)p] != stamp) {
                        seen[(size_t)p] = stamp;
                        cnt[(size_t)p] = 1;
                        plist.push_back(p);
                    } else cnt[(size_t)p]++;
                }
                int c0 = (seen[(size_t)p0] == stamp) ? cnt[(size_t)p0] : 0;

                int bestp = p0;
                int bestc = c0;
                int bestsz = sz[(size_t)p0];

                for (int p : plist) {
                    if (p == p0) continue;
                    if (sz[(size_t)p] >= cap) continue;
                    int c = cnt[(size_t)p];
                    if (c > bestc || (c == bestc && sz[(size_t)p] < bestsz)) {
                        bestc = c;
                        bestsz = sz[(size_t)p];
                        bestp = p;
                    }
                }
                if (bestp != p0 && bestc > c0) {
                    sz[(size_t)p0]--;
                    sz[(size_t)bestp]++;
                    part[(size_t)v] = bestp;
                }
            }
        } else {
            for (int v = n - 1; v >= 0; v--) {
                int p0 = part[(size_t)v];
                stamp++;
                plist.clear();
                uint64_t l = off[(size_t)v], r = off[(size_t)v + 1];
                for (uint64_t e = l; e < r; e++) {
                    int p = part[(size_t)adj[e]];
                    if (seen[(size_t)p] != stamp) {
                        seen[(size_t)p] = stamp;
                        cnt[(size_t)p] = 1;
                        plist.push_back(p);
                    } else cnt[(size_t)p]++;
                }
                int c0 = (seen[(size_t)p0] == stamp) ? cnt[(size_t)p0] : 0;

                int bestp = p0;
                int bestc = c0;
                int bestsz = sz[(size_t)p0];

                for (int p : plist) {
                    if (p == p0) continue;
                    if (sz[(size_t)p] >= cap) continue;
                    int c = cnt[(size_t)p];
                    if (c > bestc || (c == bestc && sz[(size_t)p] < bestsz)) {
                        bestc = c;
                        bestsz = sz[(size_t)p];
                        bestp = p;
                    }
                }
                if (bestp != p0 && bestc > c0) {
                    sz[(size_t)p0]--;
                    sz[(size_t)bestp]++;
                    part[(size_t)v] = bestp;
                }
            }
        }
    }

    FastOutput fo;
    for (int i = 0; i < n; i++) {
        fo.writeInt(part[(size_t)i], (i + 1 == n) ? '\n' : ' ');
    }
    fo.flush();
    return 0;
}