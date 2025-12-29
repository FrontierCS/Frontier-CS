#include <bits/stdc++.h>
using namespace std;

// Random generator: splitmix64
static uint64_t splitmix64_x;
static inline uint64_t splitmix64() {
    uint64_t z = (splitmix64_x += 0x9e3779b97f4a7c15ULL);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
    return z ^ (z >> 31);
}

struct Interactor {
    // Send a sequence of operations and receive responses
    static vector<int> query(const vector<int>& ops) {
        int L = (int)ops.size();
        cout << L;
        for (int x : ops) {
            cout << " " << x;
        }
        cout << endl;
        cout.flush();
        vector<int> res(L);
        for (int i = 0; i < L; ++i) {
            if (!(cin >> res[i])) {
                // In case of EOF or error, fill with zeros to avoid UB; interactive judge won't do this.
                res[i] = 0;
            }
        }
        return res;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int subtask;
    int n;
    if (!(cin >> subtask >> n)) {
        return 0;
    }

    splitmix64_x = 0x123456789abcdef1ULL ^ (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();

    // Step A: Build a maximal independent set S using greedy toggles
    vector<char> isS(n + 1, 0);
    vector<char> isOn(n + 1, 0); // current interactor state
    vector<int> Slist;
    Slist.reserve(n);
    for (int id = 1; id <= n; ++id) {
        // Toggle id
        {
            vector<int> ops = {id};
            vector<int> res = Interactor::query(ops);
            int r = res[0];
            if (r == 0) {
                // keep id in S
                isS[id] = 1;
                isOn[id] = 1;
                Slist.push_back(id);
            } else {
                // revert
                ops = {id};
                res = Interactor::query(ops);
                isOn[id] = 0;
            }
        }
    }
    int M = (int)Slist.size();
    vector<int> Ulist;
    Ulist.reserve(n - M);
    for (int id = 1; id <= n; ++id) if (!isS[id]) Ulist.push_back(id);

    // Edge case: if M == 0 (shouldn't happen as S is maximal unless n==0), fallback to output 1..n
    if (M == 0) {
        cout << -1;
        for (int i = 1; i <= n; ++i) cout << " " << i;
        cout << endl;
        cout.flush();
        return 0;
    }

    // Step B: Assign 64-bit random codes to S nodes and perform 64 rounds to compute rbits for U
    const int K = 64;

    vector<int> sIndexOfLabel(n + 1, -1);
    for (int i = 0; i < M; ++i) sIndexOfLabel[Slist[i]] = i;

    vector<uint64_t> codeS(M);
    unordered_map<uint64_t, int> code2SLabel; // maps code to label (id)
    code2SLabel.reserve(M * 2);
    code2SLabel.max_load_factor(0.7f);
    for (int i = 0; i < M; ++i) {
        // Ensure uniqueness (unlikely collision)
        uint64_t c;
        do {
            c = splitmix64();
        } while (code2SLabel.find(c) != code2SLabel.end());
        codeS[i] = c;
        code2SLabel[c] = Slist[i];
    }

    // Precompute BitsZero[j] bitset for S indices: 1 where code bit j == 0
    int WC = (M + 63) >> 6;
    vector< vector<uint64_t> > BitsZero(K, vector<uint64_t>(WC, 0));
    for (int j = 0; j < K; ++j) {
        for (int i = 0; i < M; ++i) {
            if (((codeS[i] >> j) & 1ULL) == 0ULL) {
                BitsZero[j][i >> 6] |= (1ULL << (i & 63));
            }
        }
    }
    // Mask for the last word
    uint64_t lastMask = (M % 64 == 0) ? ~0ULL : ((1ULL << (M % 64)) - 1ULL);

    // For each U node, compute rbits via K rounds
    vector<uint64_t> rbits(n + 1, 0);

    // Pre-construct arrays of R_j lists for S nodes to optimize operations composition
    vector< vector<int> > Rj_list(K);
    for (int j = 0; j < K; ++j) {
        vector<int>& R = Rj_list[j];
        R.reserve(M / 2 + 1);
        for (int i = 0; i < M; ++i) {
            if (((codeS[i] >> j) & 1ULL) == 0ULL) {
                R.push_back(Slist[i]);
            }
        }
    }

    for (int j = 0; j < K; ++j) {
        const vector<int>& R = Rj_list[j];
        vector<int> ops;
        ops.reserve(R.size() + Ulist.size() * 2 + R.size());
        // Toggle off R
        for (int x : R) ops.push_back(x);
        // For each U: toggle u on/off
        for (int u : Ulist) {
            ops.push_back(u);
            ops.push_back(u);
        }
        // Restore R
        for (int x : R) ops.push_back(x);

        vector<int> res = Interactor::query(ops);
        int pos = 0;
        pos += (int)R.size();
        for (int idx = 0; idx < (int)Ulist.size(); ++idx) {
            int u = Ulist[idx];
            int bit = res[pos++];
            // off toggle result ignored
            pos++;
            if (bit) rbits[u] |= (1ULL << j);
        }
        // skip restores
        // (int)R.size() responses remain to be skipped
        // But we don't need res further
    }

    // Now decode neighbors
    // adj list for all nodes 1..n
    vector< array<int, 2> > adj(n + 1, array<int, 2>{-1, -1});
    vector<int> deg(n + 1, 0);

    auto add_edge = [&](int a, int b) {
        if (deg[a] < 2) adj[a][deg[a]++] = b;
        if (deg[b] < 2) adj[b][deg[b]++] = a;
    };

    // For tracking S to U adjacency counts
    vector< vector<int> > UneighborsOfS(n + 1);
    UneighborsOfS.assign(n + 1, {});

    // First handle deg1 U: rbits[u] equals some S code
    vector<char> isDeg1U(n + 1, 0);
    vector<char> isDeg2U(n + 1, 0);
    vector< array<int, 2> > N_S_of_U(n + 1); // store S neighbors for each U (1 or 2)
    for (int u : Ulist) {
        auto it = code2SLabel.find(rbits[u]);
        if (it != code2SLabel.end()) {
            int s = it->second;
            isDeg1U[u] = 1;
            N_S_of_U[u][0] = s;
            N_S_of_U[u][1] = -1;
            add_edge(u, s);
            UneighborsOfS[s].push_back(u);
        }
    }

    // Handle deg2 U: decode pair of S using zero-bit intersection
    // Precompute pre-allocated arrays to avoid realloc
    vector<uint64_t> cand(WC);
    for (int u : Ulist) {
        if (isDeg1U[u]) continue;
        uint64_t r = rbits[u];
        // Build candidate bitset: indices i of S such that for all j where r bit is 0, codeS[i] bit j is 0
        // Start with all ones
        for (int w = 0; w < WC; ++w) cand[w] = ~0ULL;
        // Apply last word mask
        cand[WC - 1] &= lastMask;
        for (int j = 0; j < K; ++j) {
            if (((r >> j) & 1ULL) == 0ULL) {
                // intersect with BitsZero[j]
                const vector<uint64_t>& bz = BitsZero[j];
                for (int w = 0; w < WC; ++w) cand[w] &= bz[w];
            }
        }
        // Extract candidate S indices
        vector<int> candidates;
        for (int w = 0; w < WC; ++w) {
            uint64_t x = cand[w];
            while (x) {
                int b = __builtin_ctzll(x);
                int idxS = (w << 6) + b;
                if (idxS < M) candidates.push_back(idxS);
                x &= x - 1ULL;
            }
        }
        // Among candidates, find pair whose OR equals r
        int s1 = -1, s2 = -1;
        if (candidates.size() == 1) {
            // This would imply deg1, but we already handled those
            // As fallback, set s1 to the single candidate, but we need two neighbors; we will try to find second by scanning Slist (rare).
            int idx = candidates[0];
            uint64_t c1 = codeS[idx];
            // find s2: codeS[idx2] such that c1 | codeS[idx2] == r
            bool found = false;
            for (int j = 0; j < M; ++j) {
                if (j == idx) continue;
                if ( (c1 | codeS[j]) == r ) {
                    s1 = Slist[idx];
                    s2 = Slist[j];
                    found = true;
                    break;
                }
            }
            if (!found) {
                // give up and mark as deg1 erroneously; connect only one neighbor
                s1 = Slist[idx];
                s2 = -1;
            }
        } else {
            bool found = false;
            for (size_t a = 0; a < candidates.size() && !found; ++a) {
                uint64_t c1 = codeS[candidates[a]];
                for (size_t b = a + 1; b < candidates.size(); ++b) {
                    uint64_t c2 = codeS[candidates[b]];
                    if ((c1 | c2) == r) {
                        s1 = Slist[candidates[a]];
                        s2 = Slist[candidates[b]];
                        found = true;
                        break;
                    }
                }
            }
            if (!found) {
                // As a fallback (very rare), try scanning all S for a matching pair with size-limited tries
                // We will try to find any s1 in candidates and s2 in S
                bool ok = false;
                for (int idxA : candidates) {
                    uint64_t c1 = codeS[idxA];
                    for (int j = 0; j < M; ++j) {
                        if (j == idxA) continue;
                        if ((c1 | codeS[j]) == r) {
                            s1 = Slist[idxA];
                            s2 = Slist[j];
                            ok = true;
                            break;
                        }
                    }
                    if (ok) break;
                }
                if (!ok) {
                    // Very unlikely: fall back to arbitrary two from candidates if at least 2
                    if (candidates.size() >= 2) {
                        s1 = Slist[candidates[0]];
                        s2 = Slist[candidates[1]];
                    } else {
                        // give up: connect to nothing; will fail later
                        s1 = -1;
                        s2 = -1;
                    }
                }
            }
        }
        if (s1 != -1) {
            if (s2 != -1) {
                isDeg2U[u] = 1;
                N_S_of_U[u][0] = s1;
                N_S_of_U[u][1] = s2;
                add_edge(u, s1);
                add_edge(u, s2);
                UneighborsOfS[s1].push_back(u);
                UneighborsOfS[s2].push_back(u);
            } else {
                // treat as deg1 fallback
                isDeg1U[u] = 1;
                N_S_of_U[u][0] = s1;
                N_S_of_U[u][1] = -1;
                add_edge(u, s1);
                UneighborsOfS[s1].push_back(u);
            }
        } else {
            // completely failed; skip
        }
    }

    // Step D: Pair deg1 U nodes using matching via group tests
    // Identify deg1 U list
    vector<int> Udeg1;
    for (int u : Ulist) if (isDeg1U[u]) Udeg1.push_back(u);

    // Turn off all S nodes (to avoid interference)
    {
        vector<int> ops;
        ops.reserve(Slist.size());
        for (int s : Slist) {
            if (isOn[s]) {
                ops.push_back(s);
                isOn[s] = 0;
            }
        }
        if (!ops.empty()) {
            (void)Interactor::query(ops);
        }
    }

    // Build T: a maximal independent set among deg1 U nodes (graph is disjoint edges, but unknown)
    vector<char> inT(n + 1, 0);
    vector<int> Tlist;
    Tlist.reserve(Udeg1.size() / 2 + 1);
    for (int u : Udeg1) {
        // try to add u
        vector<int> res1 = Interactor::query(vector<int>{u});
        int r = res1[0];
        if (r == 0) {
            // keep u on
            inT[u] = 1;
            Tlist.push_back(u);
            isOn[u] = 1;
        } else {
            // revert
            vector<int> res2 = Interactor::query(vector<int>{u});
            isOn[u] = 0;
            (void)res2;
        }
    }

    // Now Tlist is an independent set among deg1 U nodes, so exactly one per matched pair.
    // For each v not in T (but in deg1), find partner in T using log rounds with codes
    int Tcnt = (int)Tlist.size();
    if (Tcnt > 0) {
        int KT = 0;
        while ((1 << KT) < Tcnt) ++KT;
        KT = max(KT, 1); // at least 1 round
        // Assign codes to T elements (use KT bits of a random 64-bit, but we just use lower KT bits)
        vector<uint64_t> codeT(n + 1, 0);
        unordered_map<uint64_t, int> code2T; code2T.reserve(Tcnt*2); code2T.max_load_factor(0.7f);
        for (int i = 0; i < Tcnt; ++i) {
            uint64_t c = splitmix64();
            // ensure uniqueness on lower KT bits might not be guaranteed; better use full 64 bits and map
            // But rbits will gather only KT bits; Adjust: we can use KT bits of individual's index to avoid collisions.
            // Let's instead set code = i (on KT bits).
            c = (uint64_t)i;
            codeT[Tlist[i]] = c;
            code2T[c] = Tlist[i];
        }

        vector<uint64_t> rT(n + 1, 0);
        // For each of KT bits, perform test: keep set A_j = { u in T | bit j of code is 1 }, remove others
        for (int j = 0; j < KT; ++j) {
            vector<int> R; R.reserve(Tcnt/2+1);
            for (int u : Tlist) {
                if (((codeT[u] >> j) & 1ULL) == 0ULL) R.push_back(u);
            }
            vector<int> ops;
            ops.reserve(R.size() + Udeg1.size() * 2 + R.size());
            // remove R
            for (int x : R) { ops.push_back(x); isOn[x] = 0; }
            // For each v not in T: toggle v on/off
            for (int v : Udeg1) if (!inT[v]) { ops.push_back(v); ops.push_back(v); }
            // restore R
            for (int x : R) { ops.push_back(x); isOn[x] = 1; }
            vector<int> res = Interactor::query(ops);
            int pos = 0;
            pos += (int)R.size();
            for (int v : Udeg1) if (!inT[v]) {
                int bit = res[pos++];
                pos++;
                if (bit) rT[v] |= (1ULL << j);
            }
            // skip restore responses if needed; not used
        }

        // Now decode partner for each v not in T
        for (int v : Udeg1) if (!inT[v]) {
            uint64_t code = rT[v];
            auto it = code2T.find(code);
            if (it != code2T.end()) {
                int u = it->second;
                // add edge u-v
                add_edge(u, v);
            } else {
                // fallback: if not found (unlikely), try nearest index
                // We'll compute idx round
                uint64_t idx = code & ((1ULL << KT) - 1ULL);
                int u = Tlist[(int)(idx % Tcnt)];
                add_edge(u, v);
            }
        }

        // Turn off all T nodes to clean up (not necessary, but ensure consistent end state)
        vector<int> ops_off;
        ops_off.reserve(Tcnt);
        for (int u : Tlist) if (isOn[u]) ops_off.push_back(u), isOn[u] = 0;
        if (!ops_off.empty()) {
            (void)Interactor::query(ops_off);
        }
    }

    // Now all adjacencies should be complete: each node should have degree 2
    // For S nodes, ensure they have two U neighbors
    // For deg1 U nodes, they should have 2 neighbors (one S and one deg1 U partner)
    // For deg2 U nodes, they should have 2 neighbors (two S)

    // As a sanity check, if some node has deg < 2, we won't fix; assume good.

    // Build ring ordering by traversing adjacency
    vector<int> ring;
    ring.reserve(n);
    int start = 1;
    // Ensure degree 2 for start; if not, find a node with deg==2
    if (deg[start] != 2) {
        for (int i = 1; i <= n; ++i) if (deg[i] == 2) { start = i; break; }
    }
    int prev = -1, cur = start;
    ring.push_back(cur);
    for (int step = 1; step < n; ++step) {
        int nxt = -1;
        if (deg[cur] >= 1) {
            int a = adj[cur][0];
            int b = (deg[cur] >= 2 ? adj[cur][1] : -1);
            if (a != -1 && a != prev) nxt = a;
            else if (b != -1 && b != prev) nxt = b;
        }
        if (nxt == -1) {
            // fail, try to find any not visited node
            // fallback: simple listing
            for (int i = 1; i <= n; ++i) {
                bool used = false;
                for (int x : ring) if (x == i) { used = true; break; }
                if (!used) { nxt = i; break; }
            }
        }
        prev = cur;
        cur = nxt;
        ring.push_back(cur);
    }

    // Output the permutation (any rotation or reversal is accepted)
    cout << -1;
    for (int x : ring) cout << " " << x;
    cout << endl;
    cout.flush();
    return 0;
}