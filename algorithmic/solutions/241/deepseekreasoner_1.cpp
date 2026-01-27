#include <bits/stdc++.h>
using namespace std;

vector<int> simplify(const vector<int>& M) {
    if (M.empty()) return {};
    vector<int> tmp = M;
    sort(tmp.begin(), tmp.end());
    tmp.erase(unique(tmp.begin(), tmp.end()), tmp.end());
    sort(tmp.begin(), tmp.end(), [](int a, int b) {
        return __builtin_popcount(a) < __builtin_popcount(b);
    });
    vector<int> res;
    for (int m : tmp) {
        bool minimal = true;
        for (int r : res) {
            if ((m & r) == r) {
                minimal = false;
                break;
            }
        }
        if (minimal) res.push_back(m);
    }
    return res;
}

pair<string, int> solve(vector<int> M, int n, map<vector<int>, pair<string, int>>& memo) {
    M = simplify(M);
    auto it = memo.find(M);
    if (it != memo.end()) return it->second;

    // empty -> false
    if (M.empty()) return memo[M] = {"F", 0};
    // only {0} -> true
    if (M.size() == 1 && M[0] == 0) return memo[M] = {"T", 0};

    // all monomials are singletons -> OR of variables
    bool all_single = true;
    for (int m : M) if (__builtin_popcount(m) != 1) { all_single = false; break; }
    if (all_single) {
        vector<char> vars;
        for (int m : M) vars.push_back('a' + __builtin_ctz(m));
        sort(vars.begin(), vars.end());
        if (vars.size() == 1) return memo[M] = {string(1, vars[0]), 0};
        // build right-associative OR: (v1|(v2|(...)))
        string expr = "(" + string(1, vars[0]) + "|";
        for (size_t i = 1; i < vars.size() - 1; ++i)
            expr += "(" + string(1, vars[i]) + "|";
        expr += string(1, vars.back());
        for (size_t i = 0; i < vars.size() - 1; ++i) expr += ")";
        return memo[M] = {expr, (int)vars.size() - 1};
    }

    // only one monomial -> AND of its variables
    if (M.size() == 1) {
        int bits = M[0];
        vector<char> vars;
        for (int i = 0; i < n; ++i) if (bits >> i & 1) vars.push_back('a' + i);
        sort(vars.begin(), vars.end());
        if (vars.size() == 1) return memo[M] = {string(1, vars[0]), 0};
        // build right-associative AND: (v1&(v2&(...)))
        string expr = "(" + string(1, vars[0]) + "&";
        for (size_t i = 1; i < vars.size() - 1; ++i)
            expr += "(" + string(1, vars[i]) + "&";
        expr += string(1, vars.back());
        for (size_t i = 0; i < vars.size() - 1; ++i) expr += ")";
        return memo[M] = {expr, (int)vars.size() - 1};
    }

    // special case: all minterms have exactly two variables -> check for complete bipartite AND of ORs
    bool all_size2 = true;
    for (int m : M) if (__builtin_popcount(m) != 2) { all_size2 = false; break; }
    if (all_size2) {
        vector<vector<int>> adj(n);
        for (int m : M) {
            int u = __builtin_ctz(m);
            int v = __builtin_ctz(m & (m - 1)); // second lowest bit
            adj[u].push_back(v);
            adj[v].push_back(u);
        }
        vector<int> color(n, -1);
        bool bipartite = true;
        for (int i = 0; i < n && bipartite; ++i) {
            if (color[i] == -1 && !adj[i].empty()) {
                queue<int> q;
                color[i] = 0;
                q.push(i);
                while (!q.empty()) {
                    int u = q.front(); q.pop();
                    for (int v : adj[u]) {
                        if (color[v] == -1) {
                            color[v] = color[u] ^ 1;
                            q.push(v);
                        } else if (color[v] == color[u]) {
                            bipartite = false;
                            break;
                        }
                    }
                    if (!bipartite) break;
                }
            }
        }
        if (bipartite) {
            vector<int> U, V;
            for (int i = 0; i < n; ++i) {
                if (color[i] == 0) U.push_back(i);
                else if (color[i] == 1) V.push_back(i);
            }
            // check if all edges between U and V exist
            set<pair<int, int>> edges;
            for (int m : M) {
                int u = __builtin_ctz(m);
                int v = __builtin_ctz(m & (m - 1));
                if (color[u] == 0 && color[v] == 1) edges.insert({u, v});
                else edges.insert({v, u});
            }
            bool complete = true;
            for (int u : U) {
                for (int v : V) {
                    if (!edges.count({u, v})) {
                        complete = false;
                        break;
                    }
                }
                if (!complete) break;
            }
            if (complete && !U.empty() && !V.empty()) {
                // build OR_U and OR_V
                auto build_or = [](const vector<int>& idxs) -> pair<string, int> {
                    if (idxs.size() == 1) return {string(1, 'a' + idxs[0]), 0};
                    string expr = "(" + string(1, 'a' + idxs[0]) + "|";
                    for (size_t i = 1; i < idxs.size() - 1; ++i)
                        expr += "(" + string(1, 'a' + idxs[i]) + "|";
                    expr += string(1, 'a' + idxs.back());
                    for (size_t i = 0; i < idxs.size() - 1; ++i) expr += ")";
                    return {expr, (int)idxs.size() - 1};
                };
                auto [exprU, cntU] = build_or(U);
                auto [exprV, cntV] = build_or(V);
                string expr;
                int opcnt;
                if (U.size() == 1 && V.size() == 1) {
                    expr = "(" + exprU + "&" + exprV + ")";
                    opcnt = 1;
                } else {
                    expr = "((" + exprU + ")&(" + exprV + "))";
                    opcnt = cntU + cntV + 1;
                }
                return memo[M] = {expr, opcnt};
            }
        }
    }

    // general case: try splitting by each variable
    string best_expr;
    int best_cnt = 1e9;
    vector<bool> var_used(n, false);
    for (int m : M)
        for (int i = 0; i < n; ++i)
            if (m >> i & 1) var_used[i] = true;

    for (int x = 0; x < n; ++x) if (var_used[x]) {
        vector<int> M1, M0;
        for (int m : M) {
            if (m >> x & 1) M1.push_back(m ^ (1 << x));
            else M0.push_back(m);
        }
        M1 = simplify(M1);
        M0 = simplify(M0);
        if (M1.empty()) {
            auto [e0, c0] = solve(M0, n, memo);
            if (c0 < best_cnt) best_expr = e0, best_cnt = c0;
            continue;
        }
        auto [e1, c1] = solve(M1, n, memo);
        if (M0.empty()) {
            if (e1 == "T") {
                string expr(1, 'a' + x);
                if (0 < best_cnt) best_expr = expr, best_cnt = 0;
            } else {
                string expr = "(" + string(1, 'a' + x) + "&" + e1 + ")";
                int cnt = c1 + 1;
                if (cnt < best_cnt) best_expr = expr, best_cnt = cnt;
            }
            continue;
        }
        auto [e0, c0] = solve(M0, n, memo);
        string expr = "((" + string(1, 'a' + x) + "&" + e1 + ")|" + e0 + ")";
        int cnt = c1 + c0 + 2;
        if (cnt < best_cnt) best_expr = expr, best_cnt = cnt;
    }
    return memo[M] = {best_expr, best_cnt};
}

vector<int> get_minterms(const vector<bool>& f, int n) {
    int N = 1 << n;
    vector<int> res;
    for (int mask = 0; mask < N; ++mask) {
        if (f[mask]) {
            bool minimal = true;
            for (int i = 0; i < n; ++i) {
                if (mask & (1 << i)) {
                    int sub = mask ^ (1 << i);
                    if (f[sub]) {
                        minimal = false;
                        break;
                    }
                }
            }
            if (minimal) res.push_back(mask);
        }
    }
    return res;
}

bool is_monotone(const vector<bool>& f, int n) {
    int N = 1 << n;
    for (int i = 0; i < n; ++i) {
        for (int mask = 0; mask < N; ++mask) {
            if (!(mask & (1 << i))) {
                int mask2 = mask | (1 << i);
                if (f[mask] && !f[mask2]) return false;
            }
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int T;
    cin >> T;
    while (T--) {
        int n;
        string s;
        cin >> n >> s;
        int N = 1 << n;
        vector<bool> f(N, false);
        for (int mask = 0; mask < N; ++mask) {
            f[mask] = (s[mask] == '1');
        }
        if (!is_monotone(f, n)) {
            cout << "No\n";
            continue;
        }
        cout << "Yes\n";
        vector<int> minterms = get_minterms(f, n);
        if (minterms.empty()) {
            cout << "F\n";
        } else if (find(minterms.begin(), minterms.end(), 0) != minterms.end()) {
            cout << "T\n";
        } else {
            map<vector<int>, pair<string, int>> memo;
            auto [expr, _] = solve(minterms, n, memo);
            cout << expr << "\n";
        }
    }
    return 0;
}