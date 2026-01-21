#include <bits/stdc++.h>
using namespace std;

static inline bool readInt(int &out) {
    int c = getchar_unlocked();
    if (c == EOF) return false;
    while (c != '-' && (c < '0' || c > '9')) {
        c = getchar_unlocked();
        if (c == EOF) return false;
    }
    int sgn = 1;
    if (c == '-') {
        sgn = -1;
        c = getchar_unlocked();
    }
    long long x = 0;
    while (c >= '0' && c <= '9') {
        x = x * 10 + (c - '0');
        c = getchar_unlocked();
    }
    out = (int)(x * sgn);
    return true;
}

static inline void appendInt(string &s, long long x) {
    if (x == 0) {
        s.push_back('0');
        return;
    }
    if (x < 0) {
        s.push_back('-');
        x = -x;
    }
    char buf[32];
    int n = 0;
    while (x > 0) {
        buf[n++] = char('0' + (x % 10));
        x /= 10;
    }
    while (n--) s.push_back(buf[n]);
}

struct Interact {
    int n;
    vector<unsigned char> on;
    Interact(int n_) : n(n_), on(n_ + 1, 0) {}

    int toggle1(int u) {
        // single operation query
        char buf[64];
        int len = snprintf(buf, sizeof(buf), "1 %d\n", u);
        fwrite(buf, 1, len, stdout);
        fflush(stdout);
        int ans;
        if (!readInt(ans)) exit(0);
        on[u] ^= 1;
        return ans;
    }

    void query_ops_read_ignore(const vector<int> &ops) {
        string out;
        out.reserve(16 + 12ULL * ops.size());
        appendInt(out, (long long)ops.size());
        for (int x : ops) {
            out.push_back(' ');
            appendInt(out, x);
        }
        out.push_back('\n');
        fwrite(out.data(), 1, out.size(), stdout);
        fflush(stdout);
        int ans;
        for (size_t i = 0; i < ops.size(); i++) {
            if (!readInt(ans)) exit(0);
            on[ops[i]] ^= 1;
        }
    }

    void query_ops_process_stage2(const vector<int> &ops, int diffCnt, const vector<int> &Ovec,
                                 int bit, vector<uint64_t> &respO) {
        string out;
        out.reserve(16 + 12ULL * ops.size());
        appendInt(out, (long long)ops.size());
        for (int x : ops) {
            out.push_back(' ');
            appendInt(out, x);
        }
        out.push_back('\n');
        fwrite(out.data(), 1, out.size(), stdout);
        fflush(stdout);

        int ans;
        // diff toggles
        for (int i = 0; i < diffCnt; i++) {
            if (!readInt(ans)) exit(0);
            this->on[ops[i]] ^= 1;
        }
        // for each outside u: read ans1, ans2
        int p = diffCnt;
        for (int u : Ovec) {
            (void)u;
            if (!readInt(ans)) exit(0);
            if (ans) respO[u] |= (1ULL << bit);
            // toggle u on in local? we do not track outside in `on` here, but ops includes them; update correctly:
            // ops[p] is u
            // Apply local state transitions:
            this->on[ops[p]] ^= 1;
            p++;

            if (!readInt(ans)) exit(0);
            this->on[ops[p]] ^= 1;
            p++;
        }
    }

    void query_ops_process_stage4(const vector<int> &ops, int diffCnt, const vector<int> &nonreps,
                                 int bit, vector<int> &accBits) {
        string out;
        out.reserve(16 + 12ULL * ops.size());
        appendInt(out, (long long)ops.size());
        for (int x : ops) {
            out.push_back(' ');
            appendInt(out, x);
        }
        out.push_back('\n');
        fwrite(out.data(), 1, out.size(), stdout);
        fflush(stdout);

        int ans;
        for (int i = 0; i < diffCnt; i++) {
            if (!readInt(ans)) exit(0);
            this->on[ops[i]] ^= 1;
        }
        int p = diffCnt;
        for (size_t idx = 0; idx < nonreps.size(); idx++) {
            if (!readInt(ans)) exit(0);
            if (ans) accBits[idx] |= (1 << bit);
            this->on[ops[p]] ^= 1; p++;
            if (!readInt(ans)) exit(0);
            this->on[ops[p]] ^= 1; p++;
        }
    }
};

static inline int ceil_log2_int(int x) {
    int k = 0;
    int p = 1;
    while (p < x) { p <<= 1; k++; }
    return k;
}

int main() {
    int subtask, n;
    if (!readInt(subtask)) return 0;
    if (!readInt(n)) return 0;

    Interact it(n);

    vector<unsigned char> inI(n + 1, 0);
    vector<int> Ivec;
    Ivec.reserve(n);

    // Stage 1: build maximal independent set I via greedy.
    for (int v = 1; v <= n; v++) {
        int r = it.toggle1(v);
        if (r == 0) {
            inI[v] = 1;
            Ivec.push_back(v);
        } else {
            (void)it.toggle1(v); // turn it off
        }
    }

    int m = (int)Ivec.size();
    vector<int> posI(n + 1, -1);
    for (int i = 0; i < m; i++) posI[Ivec[i]] = i;

    vector<int> Ovec;
    Ovec.reserve(n - m);
    for (int v = 1; v <= n; v++) if (!inI[v]) Ovec.push_back(v);

    // Local current on-state among I vertices (after stage1 all I are ON)
    vector<unsigned char> curOnI(m, 1);

    // For stage2, store responses in respO indexed by vertex id directly for convenience
    vector<uint64_t> respO(n + 1, 0);

    // Store decoded I-neighbors for outside vertices
    vector<unsigned char> cntInei(n + 1, 0);
    vector<int> nei1(n + 1, 0), nei2(n + 1, 0);

    // Precompute blocks
    const int K = 64;

    bool ok_stage2 = false;
    uint64_t seed_base = (uint64_t)chrono::steady_clock::now().time_since_epoch().count();

    for (int attempt = 0; attempt < 4 && !ok_stage2; attempt++) {
        // Ensure all I vertices are ON before attempt (simplify for retry)
        vector<int> ops_restore;
        ops_restore.reserve(m);
        for (int j = 0; j < m; j++) {
            if (!curOnI[j]) {
                ops_restore.push_back(Ivec[j]);
                curOnI[j] = 1;
            }
        }
        if (!ops_restore.empty()) it.query_ops_read_ignore(ops_restore);

        // Generate random 64-bit codes for I vertices
        mt19937_64 rng(seed_base + 1234567ULL * (attempt + 1));
        vector<uint64_t> codeI(m);
        codeI.shrink_to_fit(); // no-op for performance in most libs
        codeI.resize(m);
        for (int j = 0; j < m; j++) {
            uint64_t x = rng();
            if (x == 0) x = 0x9e3779b97f4a7c15ULL ^ (uint64_t)Ivec[j];
            codeI[j] = x;
        }

        unordered_map<uint64_t, int> codeToIdx;
        codeToIdx.reserve((size_t)m * 2 + 7);
        for (int j = 0; j < m; j++) codeToIdx[codeI[j]] = j;

        // Build Z bitsets: Z[i] bit j = 1 if codeI[j] has bit i == 0
        int B = (m + 63) / 64;
        uint64_t lastMask = (m % 64 == 0) ? ~0ULL : ((1ULL << (m % 64)) - 1ULL);
        vector<array<uint64_t, 1>> dummy; // to avoid accidental huge template instantiations
        (void)dummy;

        vector<vector<uint64_t>> Z(K, vector<uint64_t>(B, 0ULL));
        for (int j = 0; j < m; j++) {
            uint64_t c = codeI[j];
            int blk = j >> 6;
            int off = j & 63;
            uint64_t bit = 1ULL << off;
            for (int i = 0; i < K; i++) {
                if (((c >> i) & 1ULL) == 0ULL) Z[i][blk] |= bit;
            }
        }
        if (B > 0) {
            for (int i = 0; i < K; i++) Z[i][B - 1] &= lastMask;
        }

        // Reset respO
        for (int u : Ovec) respO[u] = 0;

        // Stage2 queries: for each bit i, set S = {I vertices with code bit i == 1}, then test all outside vertices.
        vector<int> ops;
        ops.reserve((size_t)m + 2ULL * Ovec.size() + 16);

        for (int bit = 0; bit < K; bit++) {
            ops.clear();
            int diffCnt = 0;
            for (int j = 0; j < m; j++) {
                unsigned char want = (unsigned char)((codeI[j] >> bit) & 1ULL);
                if (curOnI[j] != want) {
                    ops.push_back(Ivec[j]);
                    curOnI[j] = want;
                    diffCnt++;
                }
            }
            for (int u : Ovec) {
                ops.push_back(u);
                ops.push_back(u);
            }
            it.query_ops_process_stage2(ops, diffCnt, Ovec, bit, respO);
        }

        // Decode
        bool bad = false;
        // reset neighbor data for outside
        for (int u : Ovec) cntInei[u] = 0;

        // For I degree check: each I vertex should appear exactly twice among outside decoded links
        vector<int> IcntOut(m, 0);
        vector<array<int, 2>> IneiOut(m, array<int, 2>{0, 0});

        // temp buffer for candidate bitset and list
        vector<uint64_t> tmp;
        tmp.resize(B);

        for (int u : Ovec) {
            uint64_t r = respO[u];
            auto itf = codeToIdx.find(r);
            if (itf != codeToIdx.end()) {
                int idx = itf->second;
                cntInei[u] = 1;
                nei1[u] = Ivec[idx];
                // update I
                int &c = IcntOut[idx];
                if (c >= 2) { bad = true; break; }
                IneiOut[idx][c++] = u;
            } else {
                // find pair (a,b) such that code[a] | code[b] == r
                // candidates = intersection over bits where r has 0 of Z[bit]
                if (B > 0) {
                    for (int b = 0; b < B - 1; b++) tmp[b] = ~0ULL;
                    tmp[B - 1] = lastMask;
                }

                uint64_t notr = ~r;
                while (notr) {
                    int bit0 = __builtin_ctzll(notr);
                    notr &= notr - 1;
                    auto &Zi = Z[bit0];
                    for (int b = 0; b < B; b++) tmp[b] &= Zi[b];
                }

                vector<int> cand;
                cand.reserve(16);
                for (int b = 0; b < B; b++) {
                    uint64_t x = tmp[b];
                    while (x) {
                        int t = __builtin_ctzll(x);
                        int idx = (b << 6) + t;
                        if (idx < m) cand.push_back(idx);
                        x &= x - 1;
                        if ((int)cand.size() > 128) break;
                    }
                    if ((int)cand.size() > 128) break;
                }

                int a = -1, bidx = -1;
                // try pairs
                for (int i = 0; i < (int)cand.size() && a == -1; i++) {
                    uint64_t ci = codeI[cand[i]];
                    for (int j = i + 1; j < (int)cand.size(); j++) {
                        if ((ci | codeI[cand[j]]) == r) {
                            a = cand[i];
                            bidx = cand[j];
                            break;
                        }
                    }
                }
                if (a == -1) { bad = true; break; }

                cntInei[u] = 2;
                nei1[u] = Ivec[a];
                nei2[u] = Ivec[bidx];

                // update I degrees
                int &c1 = IcntOut[a];
                if (c1 >= 2) { bad = true; break; }
                IneiOut[a][c1++] = u;

                int &c2 = IcntOut[bidx];
                if (c2 >= 2) { bad = true; break; }
                IneiOut[bidx][c2++] = u;
            }
        }

        if (!bad) {
            for (int j = 0; j < m; j++) {
                if (IcntOut[j] != 2) { bad = true; break; }
            }
        }

        // ensure every outside got decoded
        if (!bad) {
            for (int u : Ovec) {
                if (cntInei[u] == 0 || cntInei[u] > 2) { bad = true; break; }
                if (cntInei[u] == 2 && nei1[u] == nei2[u]) { bad = true; break; }
            }
        }

        if (!bad) ok_stage2 = true;
    }

    if (!ok_stage2) {
        // Fallback: output identity permutation
        string out;
        out.reserve(4 + 12ULL * n);
        out += "-1";
        for (int i = 1; i <= n; i++) {
            out.push_back(' ');
            appendInt(out, i);
        }
        out.push_back('\n');
        fwrite(out.data(), 1, out.size(), stdout);
        fflush(stdout);
        return 0;
    }

    // Clear all I vertices (currently some subset may be ON). We'll toggle ON ones off.
    vector<int> ops_clearI;
    ops_clearI.reserve(m);
    for (int j = 0; j < m; j++) {
        int v = Ivec[j];
        if (it.on[v]) ops_clearI.push_back(v);
    }
    if (!ops_clearI.empty()) it.query_ops_read_ignore(ops_clearI);

    // Build H list: outside vertices with exactly one I neighbor
    vector<int> H;
    H.reserve(Ovec.size());
    for (int u : Ovec) if (cntInei[u] == 1) H.push_back(u);

    // Matching stage only if H not empty
    vector<unsigned char> inJ(n + 1, 0);
    vector<int> reps;
    vector<int> nonreps;
    vector<int> partnerIdx;

    if (!H.empty()) {
        // Stage3: build maximal independent set J in the matching on H.
        reps.reserve(H.size() / 2 + 1);
        for (int u : H) {
            int r = it.toggle1(u);
            if (r == 0) {
                inJ[u] = 1;
                reps.push_back(u);
            } else {
                (void)it.toggle1(u); // turn off
            }
        }

        nonreps.reserve(H.size() - reps.size());
        for (int u : H) if (!inJ[u]) nonreps.push_back(u);

        int rsz = (int)reps.size();
        if (rsz == 0) {
            // should not happen unless H empty; but handle
        } else {
            int k2 = ceil_log2_int(rsz);
            if (k2 == 0) k2 = 1;

            // current subset among reps: after greedy, all reps are ON
            vector<unsigned char> curOnR(rsz, 1);

            partnerIdx.assign(nonreps.size(), 0);

            vector<int> ops;
            ops.reserve((size_t)rsz + 2ULL * nonreps.size() + 16);

            for (int bit = 0; bit < k2; bit++) {
                ops.clear();
                int diffCnt = 0;
                for (int i = 0; i < rsz; i++) {
                    unsigned char want = (unsigned char)((i >> bit) & 1);
                    if (curOnR[i] != want) {
                        ops.push_back(reps[i]);
                        curOnR[i] = want;
                        diffCnt++;
                    }
                }
                for (int u : nonreps) {
                    ops.push_back(u);
                    ops.push_back(u);
                }
                it.query_ops_process_stage4(ops, diffCnt, nonreps, bit, partnerIdx);
            }

            // Validate indices
            vector<int> used(rsz, 0);
            for (size_t i = 0; i < nonreps.size(); i++) {
                if (partnerIdx[i] < 0 || partnerIdx[i] >= rsz) {
                    // fallback identity
                    string out;
                    out.reserve(4 + 12ULL * n);
                    out += "-1";
                    for (int v = 1; v <= n; v++) { out.push_back(' '); appendInt(out, v); }
                    out.push_back('\n');
                    fwrite(out.data(), 1, out.size(), stdout);
                    fflush(stdout);
                    return 0;
                }
                used[partnerIdx[i]]++;
            }
            // If something is off, still proceed; interactive randomness should prevent.
        }
    }

    // Build full adjacency list
    vector<array<int, 2>> adj(n + 1, array<int, 2>{0, 0});
    vector<unsigned char> deg(n + 1, 0);

    auto addEdge = [&](int a, int b) {
        if (a < 1 || a > n || b < 1 || b > n) return;
        if (deg[a] < 2) adj[a][deg[a]++] = b;
        if (deg[b] < 2) adj[b][deg[b]++] = a;
    };

    for (int u : Ovec) {
        if (cntInei[u] == 1) addEdge(u, nei1[u]);
        else if (cntInei[u] == 2) { addEdge(u, nei1[u]); addEdge(u, nei2[u]); }
    }

    if (!H.empty()) {
        int rsz = (int)reps.size();
        for (size_t i = 0; i < nonreps.size(); i++) {
            int u = nonreps[i];
            int p = partnerIdx[i];
            if (p < 0) p = 0;
            if (p >= rsz) p = rsz - 1;
            int v = reps[p];
            addEdge(u, v);
        }
    }

    // Traverse cycle to output permutation
    vector<int> order;
    order.reserve(n);
    vector<unsigned char> vis(n + 1, 0);

    int start = 1;
    int prev = 0, cur = start;
    for (int i = 0; i < n; i++) {
        order.push_back(cur);
        vis[cur] = 1;
        int a = adj[cur][0], b = adj[cur][1];
        int nxt = (a != prev ? a : b);
        prev = cur;
        cur = nxt;
        if (cur == 0) break;
    }

    // If traversal didn't cover all, try to find any start that works
    if ((int)order.size() != n || cur != start) {
        int s2 = 1;
        for (int v = 1; v <= n; v++) if (deg[v] == 2) { s2 = v; break; }
        order.clear();
        prev = 0; cur = s2;
        for (int i = 0; i < n; i++) {
            order.push_back(cur);
            int a = adj[cur][0], b = adj[cur][1];
            int nxt = (a != prev ? a : b);
            prev = cur;
            cur = nxt;
            if (cur == 0) break;
        }
        if ((int)order.size() != n) {
            order.clear();
            for (int v = 1; v <= n; v++) order.push_back(v);
        }
    }

    // Output
    string out;
    out.reserve(4 + 12ULL * n);
    out += "-1";
    for (int i = 0; i < n; i++) {
        out.push_back(' ');
        appendInt(out, order[i]);
    }
    out.push_back('\n');
    fwrite(out.data(), 1, out.size(), stdout);
    fflush(stdout);
    return 0;
}