#include <bits/stdc++.h>
using namespace std;

using ll = long long;

struct QueryResult {
    ll s, t;
    vector<ll> dist;
};

QueryResult ask(ll s, ll t, int k) {
    QueryResult qr;
    qr.s = s;
    qr.t = t;
    qr.dist.assign(k, 0);
    cout << "? 1 " << s << " " << t << endl;
    cout.flush();
    for (int i = 0; i < k; ++i) {
        if (!(cin >> qr.dist[i])) {
            exit(0);
        }
    }
    return qr;
}

struct Edge {
    int v;
    int x, y;
    int lab[3]; // indices of distances for up to 3 pairing queries
};

// Globals for DFS-based matching
int G_k;
int G_PQ;
vector<vector<Edge>> G_adj;
vector<vector<int>> G_remainingFreq;
vector<vector<ll>> G_uniqDist;
vector<int> G_matchU, G_matchV;

bool dfs_match(int assignedCount) {
    if (assignedCount == G_k) return true;

    int bestU = -1;
    vector<int> candEdgeIdx;
    int bestCnt = INT_MAX;

    // choose unassigned U with minimum number of viable edges
    for (int u = 0; u < G_k; ++u) {
        if (G_matchU[u] != -1) continue;
        vector<int> curCand;
        for (int ei = 0; ei < (int)G_adj[u].size(); ++ei) {
            const Edge &e = G_adj[u][ei];
            if (G_matchV[e.v] != -1) continue;
            bool ok = true;
            for (int q = 0; q < G_PQ; ++q) {
                if (G_remainingFreq[q][e.lab[q]] <= 0) {
                    ok = false;
                    break;
                }
            }
            if (!ok) continue;
            curCand.push_back(ei);
        }
        if (curCand.empty()) return false;
        if ((int)curCand.size() < bestCnt) {
            bestCnt = (int)curCand.size();
            bestU = u;
            candEdgeIdx.swap(curCand);
            if (bestCnt == 1) break; // cannot do better
        }
    }

    int u = bestU;
    for (int idx : candEdgeIdx) {
        Edge &e = G_adj[u][idx];
        int v = e.v;
        if (G_matchV[v] != -1) continue;

        // apply choice
        G_matchU[u] = v;
        G_matchV[v] = u;
        for (int q = 0; q < G_PQ; ++q) {
            G_remainingFreq[q][e.lab[q]]--;
        }

        bool ok = true;

        // feasibility check
        for (int q = 0; q < G_PQ && ok; ++q) {
            int M = (int)G_uniqDist[q].size();
            vector<int> possible(M, 0);
            for (int uu = 0; uu < G_k; ++uu) {
                if (G_matchU[uu] != -1) continue;
                for (const Edge &ee : G_adj[uu]) {
                    if (G_matchV[ee.v] != -1) continue;
                    possible[ee.lab[q]]++;
                }
            }
            for (int d = 0; d < M; ++d) {
                if (possible[d] < G_remainingFreq[q][d]) {
                    ok = false;
                    break;
                }
            }
        }

        if (ok && dfs_match(assignedCount + 1)) return true;

        // backtrack
        for (int q = 0; q < G_PQ; ++q) {
            G_remainingFreq[q][e.lab[q]]++;
        }
        G_matchU[u] = -1;
        G_matchV[v] = -1;
    }

    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int b, k, w;
    if (!(cin >> b >> k >> w)) {
        return 0;
    }
    ll B = b;

    // Always do first two queries to obtain sums U = x+y and V = x-y
    QueryResult q1 = ask(B, B, k);      // (b, b)  -> U set
    QueryResult q2 = ask(B, -B, k);     // (b, -b) -> V set
    int queriesUsed = 2;

    int maxExtra = max(0, w - queriesUsed);
    int PQ = min(3, maxExtra); // number of additional pairing queries (0..3)

    vector<QueryResult> pairQueries;
    if (PQ >= 1) {
        pairQueries.push_back(ask(0, 0, k));
        ++queriesUsed;
    }
    if (PQ >= 2) {
        pairQueries.push_back(ask(0, B, k));
        ++queriesUsed;
    }
    if (PQ >= 3) {
        pairQueries.push_back(ask(B, 0, k));
        ++queriesUsed;
    }

    // Build U and V multisets from first two queries
    vector<ll> U(k), V(k);
    for (int i = 0; i < k; ++i) {
        U[i] = 2 * B - q1.dist[i]; // u_i = x_i + y_i
        V[i] = 2 * B - q2.dist[i]; // v_i = x_i - y_i
    }

    // Prepare distance information for pairing queries
    vector<vector<ll>> uniqDist(PQ);
    vector<vector<int>> freqDist(PQ);
    vector<map<ll,int>> distIndex(PQ);

    for (int q = 0; q < PQ; ++q) {
        auto d = pairQueries[q].dist;   // sorted non-decreasing already
        vector<ll> &uvec = uniqDist[q];
        uvec = d;
        sort(uvec.begin(), uvec.end());
        uvec.erase(unique(uvec.begin(), uvec.end()), uvec.end());
        int M = (int)uvec.size();
        freqDist[q].assign(M, 0);
        for (ll val : d) {
            int idx = (int)(lower_bound(uvec.begin(), uvec.end(), val) - uvec.begin());
            freqDist[q][idx]++;
        }
        for (int i = 0; i < M; ++i) {
            distIndex[q][uvec[i]] = i;
        }
    }

    // Build adjacency between U indices and V indices (possible pairings)
    vector<vector<Edge>> adj(k);
    vector<vector<int>> globalEdgeCount(PQ);

    for (int q = 0; q < PQ; ++q) {
        globalEdgeCount[q].assign(uniqDist[q].size(), 0);
    }

    for (int i = 0; i < k; ++i) {
        for (int j = 0; j < k; ++j) {
            ll u = U[i], v = V[j];
            if (((u + v) & 1LL) != 0) continue; // x not integer
            ll xll = (u + v) / 2;
            ll yll = (u - v) / 2;
            if (xll < -B || xll > B || yll < -B || yll > B) continue;

            Edge e;
            e.v = j;
            e.x = (int)xll;
            e.y = (int)yll;
            bool valid = true;

            for (int q = 0; q < PQ; ++q) {
                ll s = pairQueries[q].s;
                ll t = pairQueries[q].t;
                ll dPred = llabs(xll - s) + llabs(yll - t);
                auto it = distIndex[q].find(dPred);
                if (it == distIndex[q].end()) {
                    valid = false;
                    break;
                }
                e.lab[q] = it->second;
            }

            if (!valid) continue;

            adj[i].push_back(e);
            for (int q = 0; q < PQ; ++q) {
                globalEdgeCount[q][e.lab[q]]++;
            }
        }
    }

    // If we used pairing queries, verify edge counts cover required frequencies
    if (PQ > 0) {
        for (int q = 0; q < PQ; ++q) {
            int M = (int)uniqDist[q].size();
            for (int d = 0; d < M; ++d) {
                if (globalEdgeCount[q][d] < freqDist[q][d]) {
                    // Should not happen for valid judge data; but fallback:
                    // no consistent set -> just output dummy guesses within bounds.
                    vector<int> outX(k, 0), outY(k, 0);
                    cout << "!";
                    for (int i = 0; i < k; ++i) {
                        cout << " " << outX[i] << " " << outY[i];
                    }
                    cout << endl;
                    cout.flush();
                    return 0;
                }
            }
        }
    }

    vector<int> matchU(k, -1), matchV(k, -1);

    if (PQ == 0) {
        // No pairing distance information (w == 2). Just find any perfect matching
        // respecting parity & bounds using simple DFS-based bipartite matching.
        vector<int> mt(k, -1);
        function<bool(int, vector<int>&)> kuhn = [&](int vtx, vector<int> &used) -> bool {
            if (used[vtx]) return false;
            used[vtx] = 1;
            for (const Edge &e : adj[vtx]) {
                int to = e.v;
                if (mt[to] == -1 || kuhn(mt[to], used)) {
                    mt[to] = vtx;
                    return true;
                }
            }
            return false;
        };

        for (int vtx = 0; vtx < k; ++vtx) {
            vector<int> used(k, 0);
            kuhn(vtx, used);
        }
        for (int j = 0; j < k; ++j) {
            if (mt[j] != -1) {
                matchU[mt[j]] = j;
                matchV[j] = mt[j];
            }
        }
        // In rare case of incomplete matching (shouldn't happen), fill arbitrarily
        for (int i = 0; i < k; ++i) {
            if (matchU[i] == -1) {
                for (int j = 0; j < k; ++j) {
                    if (matchV[j] == -1) {
                        matchU[i] = j;
                        matchV[j] = i;
                        break;
                    }
                }
            }
        }
    } else {
        // Use DFS with distance-label constraints
        G_k = k;
        G_PQ = PQ;
        G_adj = adj;
        G_uniqDist = uniqDist;
        G_matchU.assign(k, -1);
        G_matchV.assign(k, -1);
        G_remainingFreq = freqDist; // copy initial frequencies

        bool ok = dfs_match(0);
        if (!ok) {
            // Fallback: extremely unlikely. Use unconstrained matching.
            vector<int> mt(k, -1);
            function<bool(int, vector<int>&)> kuhn = [&](int vtx, vector<int> &used) -> bool {
                if (used[vtx]) return false;
                used[vtx] = 1;
                for (const Edge &e : adj[vtx]) {
                    int to = e.v;
                    if (mt[to] == -1 || kuhn(mt[to], used)) {
                        mt[to] = vtx;
                        return true;
                    }
                }
                return false;
            };
            for (int vtx = 0; vtx < k; ++vtx) {
                vector<int> used(k, 0);
                kuhn(vtx, used);
            }
            for (int j = 0; j < k; ++j) {
                if (mt[j] != -1) {
                    matchU[mt[j]] = j;
                    matchV[j] = mt[j];
                }
            }
            for (int i = 0; i < k; ++i) {
                if (matchU[i] == -1) {
                    for (int j = 0; j < k; ++j) {
                        if (matchV[j] == -1) {
                            matchU[i] = j;
                            matchV[j] = i;
                            break;
                        }
                    }
                }
            }
        } else {
            matchU = G_matchU;
            matchV = G_matchV;
        }
    }

    // Construct final coordinates
    vector<int> outX(k), outY(k);
    for (int i = 0; i < k; ++i) {
        int j = matchU[i];
        if (j < 0 || j >= k) {
            outX[i] = 0;
            outY[i] = 0;
        } else {
            ll u = U[i];
            ll v = V[j];
            ll xll = (u + v) / 2;
            ll yll = (u - v) / 2;
            if (xll < -B || xll > B || yll < -B || yll > B) {
                xll = 0;
                yll = 0;
            }
            outX[i] = (int)xll;
            outY[i] = (int)yll;
        }
    }

    cout << "!";
    for (int i = 0; i < k; ++i) {
        cout << " " << outX[i] << " " << outY[i];
    }
    cout << endl;
    cout.flush();

    return 0;
}