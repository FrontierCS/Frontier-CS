#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 1024;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if (!(cin >> N >> M)) return 0;
    vector< bitset<MAXN> > adj(N);
    for (int i = 0; i < M; ++i) {
        int u, v; cin >> u >> v;
        if (u == v) continue;
        --u; --v;
        adj[u].set(v);
        adj[v].set(u);
    }
    // Build adjacency lists from bitsets
    vector<vector<int>> nbrs(N);
    vector<int> deg(N, 0);
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (adj[i].test(j)) nbrs[i].push_back(j);
        }
        deg[i] = (int)nbrs[i].size();
    }

    mt19937 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());
    auto start_time = chrono::steady_clock::now();
    auto elapsed = [&](){
        return chrono::duration<double>(chrono::steady_clock::now() - start_time).count();
    };

    auto greedy_build = [&](vector<char>& inS, bitset<MAXN>& Sbit) {
        inS.assign(N, 0);
        Sbit.reset();
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        vector<uint32_t> rkey(N);
        for (int i = 0; i < N; ++i) rkey[i] = rng();
        stable_sort(order.begin(), order.end(), [&](int a, int b){
            if (deg[a] != deg[b]) return deg[a] < deg[b];
            return rkey[a] < rkey[b];
        });
        bitset<MAXN> banned;
        banned.reset();
        for (int u : order) {
            if (!banned.test(u)) {
                inS[u] = 1;
                Sbit.set(u);
                banned.set(u);
                banned |= adj[u];
            }
        }
    };

    auto augment_from_free = [&](vector<char>& inS, bitset<MAXN>& Sbit, vector<int>& cnt){
        // Add any vertex not in S with cnt==0
        deque<int> dq;
        vector<char> inq(N, 0);
        for (int v = 0; v < N; ++v) {
            if (!inS[v] && cnt[v] == 0) { dq.push_back(v); inq[v]=1; }
        }
        while (!dq.empty()) {
            int v = dq.front(); dq.pop_front();
            if (inS[v]) continue;
            if (cnt[v] != 0) continue;
            // Add v
            inS[v] = 1; Sbit.set(v);
            for (int w : nbrs[v]) {
                cnt[w]++;
                // If w not inS and becomes 0 won't happen since increment
            }
            // Now some vertices that were blocked only by v need to be considered? No, adding v only increases cnt.
        }
    };

    auto local_improve = [&](vector<char>& inS, bitset<MAXN>& Sbit){
        // Initialize cnt: number of neighbors in S for each vertex
        vector<int> cnt(N, 0);
        for (int v = 0; v < N; ++v) {
            if (!inS[v]) {
                // cnt[v] = (adj[v] & Sbit).count();
                // Manual count using neighbors for speed
                int c = 0;
                for (int u : nbrs[v]) if (inS[u]) ++c;
                cnt[v] = c;
            } else {
                cnt[v] = 0;
            }
        }
        // Maximal augmentation shouldn't add anything, but ensure
        augment_from_free(inS, Sbit, cnt);

        bool improved = true;
        vector<int> Sinv;
        Sinv.reserve(N);
        while (improved && elapsed() < 1.8) {
            improved = false;
            // Build list of S vertices and shuffle
            Sinv.clear();
            for (int u = 0; u < N; ++u) if (inS[u]) Sinv.push_back(u);
            shuffle(Sinv.begin(), Sinv.end(), rng);

            for (int u : Sinv) {
                if (!inS[u]) continue;
                // Build candidate set C: vertices not in S with cnt==1 and adjacent to u
                bitset<MAXN> Cbit; Cbit.reset();
                vector<int> C;
                for (int v : nbrs[u]) {
                    if (!inS[v] && cnt[v] == 1) {
                        Cbit.set(v);
                        C.push_back(v);
                    }
                }
                if ((int)C.size() < 2) continue;

                // Compute internal degrees within C
                vector<pair<int,int>> nodes; nodes.reserve(C.size());
                for (int v : C) {
                    int degC = (int)((adj[v] & Cbit).count());
                    nodes.emplace_back(degC, v);
                }
                sort(nodes.begin(), nodes.end()); // ascending internal degree

                bitset<MAXN> picked; picked.reset();
                vector<int> pickList;
                for (auto &p : nodes) {
                    int v = p.second;
                    if (((adj[v] & picked).any())) continue;
                    picked.set(v);
                    pickList.push_back(v);
                }
                if ((int)pickList.size() >= 2) {
                    // Perform swap: remove u, add all in pickList
                    inS[u] = 0;
                    Sbit.reset(u);
                    for (int w : nbrs[u]) {
                        cnt[w] = max(0, cnt[w]-1);
                    }
                    for (int v : pickList) {
                        if (!inS[v]) {
                            inS[v] = 1; Sbit.set(v);
                            for (int w : nbrs[v]) {
                                cnt[w]++;
                            }
                        }
                    }
                    // After swap, try to augment by any free vertices
                    augment_from_free(inS, Sbit, cnt);
                    improved = true;
                    break; // restart scan of S
                }
                if (elapsed() >= 1.8) break;
            }
        }
    };

    vector<char> best_inS(N, 0), cur_inS;
    bitset<MAXN> bestS, curS;
    int bestK = -1;

    int restarts = 0;
    while (elapsed() < 1.8) {
        greedy_build(cur_inS, curS);
        local_improve(cur_inS, curS);
        int K = (int)curS.count();
        if (K > bestK) {
            bestK = K;
            best_inS = cur_inS;
            bestS = curS;
        }
        ++restarts;
        if (restarts >= 20) break; // avoid too many restarts
    }

    for (int i = 0; i < N; ++i) {
        cout << (best_inS[i] ? 1 : 0) << '\n';
    }
    return 0;
}