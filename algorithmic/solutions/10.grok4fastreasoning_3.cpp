#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        int n;
        cin >> n;
        if (n == 1) {
            cout << "!" << endl;
            cout.flush();
            continue;
        }
        auto query = [&](int u, int v) -> long long {
            if (u == v) return 0;
            cout << "? " << u << " " << v << endl;
            cout.flush();
            long long d;
            cin >> d;
            return d;
        };
        auto get_dist = [&](int root, int nn) -> vector<long long> {
            vector<long long> d(nn + 1, 0);
            for (int v = 1; v <= nn; ++v) {
                if (v != root) {
                    d[v] = query(root, v);
                }
            }
            return d;
        };
        auto d1 = get_dist(1, n);
        int a = 1;
        for (int v = 1; v <= n; ++v) {
            if (d1[v] > d1[a]) a = v;
        }
        vector<long long> da = get_dist(a, n);
        int b = 1;
        for (int v = 1; v <= n; ++v) {
            if (da[v] > da[b]) b = v;
        }
        vector<long long> db = get_dist(b, n);
        long long dist_ab = da[b];
        vector<pair<long long, int>> onpath_init;
        for (int v = 1; v <= n; ++v) {
            if (da[v] + db[v] == dist_ab) {
                onpath_init.emplace_back(da[v], v);
            }
        }
        sort(onpath_init.begin(), onpath_init.end());
        vector<int> path;
        for (auto& p : onpath_init) path.push_back(p.second);
        vector<tuple<int, int, long long>> edges;
        for (size_t i = 0; i + 1 < onpath_init.size(); ++i) {
            int u = onpath_init[i].second;
            int v = onpath_init[i + 1].second;
            long long w = onpath_init[i + 1].first - onpath_init[i].first;
            edges.emplace_back(u, v, w);
        }
        map<long long, int> da_to_idx;
        for (size_t i = 0; i < onpath_init.size(); ++i) {
            da_to_idx[onpath_init[i].first] = i;
        }
        vector<bool> is_on_path(n + 1, false);
        for (int p : path) is_on_path[p] = true;
        vector<vector<int>> hangs(path.size());
        for (int v = 1; v <= n; ++v) {
            if (is_on_path[v]) continue;
            long long cand = (da[v] + dist_ab - db[v]) / 2;
            auto it = da_to_idx.find(cand);
            if (it != da_to_idx.end()) {
                int id = it->second;
                hangs[id].push_back(v);
            }
        }
        auto reconstruct = [&](auto&& self, int rt, vector<int> S, function<long long(int)> get_dist_rt) -> void {
            if (S.empty()) return;
            int l = S[0];
            long long maxd = get_dist_rt(l);
            for (int s : S) {
                long long dd = get_dist_rt(s);
                if (dd > maxd) {
                    maxd = dd;
                    l = s;
                }
            }
            vector<long long> dl(n + 1, -1);
            dl[l] = 0;
            dl[rt] = query(l, rt);
            for (int s : S) {
                if (s != l) {
                    dl[s] = query(l, s);
                }
            }
            vector<pair<long long, int>> onpath;
            onpath.emplace_back(0LL, rt);
            for (int s : S) {
                if (get_dist_rt(s) + dl[s] == maxd) {
                    onpath.emplace_back(get_dist_rt(s), s);
                }
            }
            sort(onpath.begin(), onpath.end());
            for (size_t j = 0; j + 1 < onpath.size(); ++j) {
                int u = onpath[j].second;
                int v = onpath[j + 1].second;
                long long w = onpath[j + 1].first - onpath[j].first;
                edges.emplace_back(u, v, w);
            }
            vector<vector<int>> subhangs(onpath.size());
            set<int> onpath_set;
            for (auto& p : onpath) onpath_set.insert(p.second);
            for (int s : S) {
                if (onpath_set.count(s)) continue;
                long long cand = (get_dist_rt(s) + maxd - dl[s]) / 2;
                auto it = lower_bound(onpath.begin(), onpath.end(), make_pair(cand, 0));
                if (it != onpath.end() && it->first == cand) {
                    size_t j = it - onpath.begin();
                    subhangs[j].push_back(s);
                }
            }
            for (size_t j = 0; j < onpath.size(); ++j) {
                int q = onpath[j].second;
                vector<int> subS = subhangs[j];
                if (subS.empty()) continue;
                auto sub_get_dist = [get_dist_rt, q](int ss) -> long long {
                    return get_dist_rt(ss) - get_dist_rt(q);
                };
                self(self, q, subS, sub_get_dist);
            }
        };
        for (size_t i = 0; i < path.size(); ++i) {
            int pi = path[i];
            vector<int> Si = hangs[i];
            if (!Si.empty()) {
                auto get_d = [&](int v) -> long long {
                    return da[v] - da[pi];
                };
                reconstruct(reconstruct, pi, Si, get_d);
            }
        }
        cout << "!";
        for (size_t i = 0; i < edges.size(); ++i) {
            auto [u, v, w] = edges[i];
            cout << " " << u << " " << v << " " << w;
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}