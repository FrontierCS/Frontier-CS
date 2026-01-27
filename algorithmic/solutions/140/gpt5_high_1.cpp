#include <bits/stdc++.h>
using namespace std;

using ll = long long;

static const ll INF64 = (ll)4e18;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    ll b;
    int k, w;
    if (!(cin >> b >> k >> w)) {
        return 0;
    }
    ll M = b; // choose M = b to ensure |x - (+/-M)| and |y - (+/-M)| linearize

    auto ask = [&](ll sx, ll ty) -> vector<ll> {
        cout << "? 1 " << sx << " " << ty << "\n";
        cout.flush();
        vector<ll> res(k);
        for (int i = 0; i < k; ++i) {
            if (!(cin >> res[i])) {
                // If judge is not available, exit gracefully
                exit(0);
            }
        }
        return res;
    };

    // Query at (-M, +M) and (-M, -M)
    vector<ll> A1 = ask(-M, +M); // A1_i = x_i + 2M - y_i
    vector<ll> B1 = ask(-M, -M); // B1_i = x_i + 2M + y_i

    // Optionally query (0,0) if allowed
    bool useC = false;
    vector<ll> C;
    if (w >= 3) {
        C = ask(0, 0); // C_i = |x_i| + |y_i|
        useC = true;
    }

    // Build L and R sets
    vector<ll> L(k), R(k);
    for (int i = 0; i < k; ++i) {
        L[i] = A1[i] - 2 * M; // x_i - y_i
        R[i] = B1[i] - 2 * M; // x_i + y_i
    }

    // Prepare counts for additional waves
    unordered_map<ll,int> countC;
    if (useC) {
        for (ll v : C) countC[v]++;
    }

    // Build adjacency: from L indices to R indices
    vector<vector<int>> adj(k);
    auto inRange = [&](ll x, ll y) -> bool {
        return (-b <= x && x <= b && -b <= y && y <= b);
    };

    for (int i = 0; i < k; ++i) {
        for (int j = 0; j < k; ++j) {
            ll Li = L[i], Rj = R[j];
            if (((Li + Rj) & 1LL) != 0) continue; // parity check
            ll x = (Li + Rj) / 2;
            ll y = (Rj - Li) / 2;
            if (!inRange(x, y)) continue;
            if (useC) {
                ll d = ll(llabs(x - 0) + llabs(y - 0));
                if (countC.find(d) == countC.end()) continue;
            }
            adj[i].push_back(j);
        }
    }

    // If we have the (0,0) wave, use backtracking with counts to ensure exact matching
    vector<pair<ll,ll>> result(k, {0,0});
    vector<int> order(k);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b){ return adj[a].size() < adj[b].size(); });

    vector<int> usedR(k, 0);

    function<bool(int, unordered_map<ll,int>&)> dfs = [&](int pos, unordered_map<ll,int>& cntC) -> bool {
        if (pos == k) {
            if (useC) {
                for (auto &p : cntC) {
                    if (p.second != 0) return false;
                }
            }
            return true;
        }
        int i = order[pos];
        // If no candidates, fail
        if (adj[i].empty()) return false;

        // Try each candidate R index
        for (int j : adj[i]) {
            if (usedR[j]) continue;
            ll Li = L[i], Rj = R[j];
            ll x = (Li + Rj) / 2;
            ll y = (Rj - Li) / 2;
            // For extra waves, check counts
            ll dC = 0;
            if (useC) {
                dC = ll(llabs(x) + llabs(y));
                auto it = cntC.find(dC);
                if (it == cntC.end() || it->second <= 0) continue;
                it->second--;
            }

            usedR[j] = 1;
            result[i] = {x, y};
            if (dfs(pos + 1, cntC)) return true;
            usedR[j] = 0;

            if (useC) {
                cntC[dC]++;
            }
        }
        return false;
    };

    bool solved = false;

    if (useC) {
        unordered_map<ll,int> cntC = countC;
        solved = dfs(0, cntC);
    } else {
        // Without extra constraints, find any perfect matching using Hopcroft-Karp
        // Build graph and run HK
        // Hopcroft-Karp
        vector<int> dist(k, -1);
        vector<int> matchL(k, -1), matchR(k, -1);

        function<bool()> bfs = [&]() {
            queue<int> q;
            for (int i = 0; i < k; ++i) {
                if (matchL[i] == -1) {
                    dist[i] = 0;
                    q.push(i);
                } else {
                    dist[i] = -1;
                }
            }
            bool found = false;
            while (!q.empty()) {
                int v = q.front(); q.pop();
                for (int to : adj[v]) {
                    int u = matchR[to];
                    if (u != -1) {
                        if (dist[u] == -1) {
                            dist[u] = dist[v] + 1;
                            q.push(u);
                        }
                    } else {
                        found = true;
                    }
                }
            }
            return found;
        };

        function<bool(int)> dfsHK = [&](int v) {
            for (int to : adj[v]) {
                int u = matchR[to];
                if (u == -1 || (dist[u] == dist[v] + 1 && dfsHK(u))) {
                    matchL[v] = to;
                    matchR[to] = v;
                    return true;
                }
            }
            dist[v] = -1;
            return false;
        };

        int matching = 0;
        while (bfs()) {
            for (int i = 0; i < k; ++i) {
                if (matchL[i] == -1 && dfsHK(i)) {
                    matching++;
                }
            }
        }
        if (matching == k) {
            for (int i = 0; i < k; ++i) {
                int j = matchL[i];
                ll x = (L[i] + R[j]) / 2;
                ll y = (R[j] - L[i]) / 2;
                result[i] = {x, y};
            }
            solved = true;
        } else {
            solved = false;
        }
    }

    if (!solved) {
        // As a fallback (should be rare), try adding more constraints if allowed
        // We'll query (1,0) and try again
        if (w >= 4) {
            vector<ll> D = ask(1, 0); // d = |x-1| + |y|
            unordered_map<ll,int> countD;
            for (ll v : D) countD[v]++;

            // Rebuild adjacency (no change), run backtracking with both C and D
            vector<int> usedR2(k, 0);
            vector<pair<ll,ll>> result2(k, {0,0});

            unordered_map<ll,int> cntC2 = countC; // maybe empty if not asked C
            unordered_map<ll,int> cntD2 = countD;

            function<bool(int)> dfs2 = [&](int pos) -> bool {
                if (pos == k) {
                    for (auto &p : cntC2) if (p.second != 0) return false;
                    for (auto &p : cntD2) if (p.second != 0) return false;
                    return true;
                }
                int i = order[pos];
                if (adj[i].empty()) return false;
                for (int j : adj[i]) {
                    if (usedR2[j]) continue;
                    ll Li = L[i], Rj = R[j];
                    ll x = (Li + Rj) / 2;
                    ll y = (Rj - Li) / 2;

                    // Check C
                    if (useC) {
                        ll dC = ll(llabs(x) + llabs(y));
                        auto itC = cntC2.find(dC);
                        if (itC == cntC2.end() || itC->second <= 0) continue;
                        itC->second--;
                        // Check D
                        ll dD = ll(llabs(x - 1) + llabs(y));
                        auto itD = cntD2.find(dD);
                        if (itD == cntD2.end() || itD->second <= 0) { itC->second++; continue; }
                        itD->second--;

                        usedR2[j] = 1;
                        result2[i] = {x, y};
                        if (dfs2(pos + 1)) { result = result2; return true; }
                        usedR2[j] = 0;

                        itD->second++;
                        itC->second++;
                    } else {
                        // Only D constraint
                        ll dD = ll(llabs(x - 1) + llabs(y));
                        auto itD = cntD2.find(dD);
                        if (itD == cntD2.end() || itD->second <= 0) continue;
                        itD->second--;

                        usedR2[j] = 1;
                        result2[i] = {x, y};
                        if (dfs2(pos + 1)) { result = result2; return true; }
                        usedR2[j] = 0;

                        itD->second++;
                    }
                }
                return false;
            };

            if (dfs2(0)) {
                solved = true;
            }
        }
    }

    // Output the result (even if not solved, output something based on whatever we have)
    cout << "!";
    for (int i = 0; i < k; ++i) {
        ll x = result[i].first;
        ll y = result[i].second;
        // If not solved, fallback to any reasonable estimate
        if (!solved) {
            // Derive from L and R pairing greedily (default): pair i with i
            ll Li = L[i], Rj = R[i % k];
            if (((Li + Rj) & 1LL) == 0) {
                x = (Li + Rj) / 2;
                y = (Rj - Li) / 2;
            } else {
                x = 0; y = 0;
            }
            if (x < -b || x > b) x = max(-b, min(b, x));
            if (y < -b || y > b) y = max(-b, min(b, y));
        }
        cout << " " << x << " " << y;
    }
    cout << "\n";
    cout.flush();

    return 0;
}