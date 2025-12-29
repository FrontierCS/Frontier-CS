#include <bits/stdc++.h>
using namespace std;

int n;
vector<int> parentt;
vector<int> col;
vector<vector<int>> parts;
vector<int> query_set(vector<int> S) {
    if (S.empty()) return {0};
    sort(S.begin(), S.end());
    auto it = unique(S.begin(), S.end());
    S.resize(distance(S.begin(), it));
    cout << "? " << S.size() << endl;
    for (int v : S) cout << v << " ";
    cout << endl;
    cout.flush();
    int m;
    cin >> m;
    if (m == -1) exit(0);
    return m;
    // wait, return int
    // mistake, query_set returns int
}

int main_query_set(const vector<int>& S) {
    vector<int> SS = S;
    if (SS.empty()) return 0;
    sort(SS.begin(), SS.end());
    auto it = unique(SS.begin(), SS.end());
    SS.resize(distance(SS.begin(), it));
    cout << "? " << SS.size() << endl;
    for (int v : SS) cout << v << " ";
    cout << endl;
    cout.flush();
    int m;
    cin >> m;
    if (m == -1) exit(0);
    return m;
}

vector<int> find_all_connected(const vector<int>& F, vector<int> group, long long known_cross, int e_F) {
    if (group.empty()) return {};
    if (group.size() == 1) {
        if (known_cross > 0) return group;
        return {};
    }
    int mid = group.size() / 2;
    vector<int> left(group.begin(), group.begin() + mid);
    vector<int> right(group.begin() + mid, group.end());
    int e_left = main_query_set(left);
    vector<int> f_left = F;
    f_left.insert(f_left.end(), left.begin(), left.end());
    int e_fleft = main_query_set(f_left);
    long long cross_left = (long long)e_fleft - e_F - e_left;
    long long cross_right = known_cross - cross_left;
    vector<int> res;
    if (cross_left > 0) {
        vector<int> sub = find_all_connected(F, left, cross_left, e_F);
        res.insert(res.end(), sub.begin(), sub.end());
    }
    if (cross_right > 0) {
        vector<int> sub = find_all_connected(F, right, cross_right, e_F);
        res.insert(res.end(), sub.begin(), sub.end());
    }
    return res;
}

int find_one_neighbor(const vector<int>& P, int u) {
    vector<int> Pu = P;
    Pu.push_back(u);
    int known = main_query_set(Pu); // e_P =0
    if (known == 0) assert(false);
    // now recursive find one
    function<int(vector<int>, long long)> rec = [&](vector<int> grp, long long kcross) -> int {
        if (grp.size() == 1) return grp[0];
        int md = grp.size() / 2;
        vector<int> lft(grp.begin(), grp.begin() + md);
        vector<int> rgt(grp.begin() + md, grp.end());
        vector<int> ulft = lft;
        ulft.push_back(u);
        int e_ul = main_query_set(ulft);
        long long cl = e_ul; // e_lft=0
        long long cr = kcross - cl;
        if (cl > 0) {
            return rec(lft, cl);
        } else {
            return rec(rgt, cr);
        }
    };
    return rec(P, known);
}

int find_one_in_group(int u, vector<int> G, int known_d) {
    // G no u, e_G may not 0
    function<int(vector<int>, long long)> rec = [&](vector<int> grp, long long kcross) -> int {
        if (grp.size() == 1) return grp[0];
        int md = grp.size() / 2;
        vector<int> lft(grp.begin(), grp.begin() + md);
        vector<int> rgt(grp.begin() + md, grp.end());
        int e_l = main_query_set(lft);
        vector<int> ulft = lft;
        ulft.push_back(u);
        int e_ul = main_query_set(ulft);
        long long cl = (long long)e_ul - e_l;
        long long cr = kcross - cl;
        if (cl > 0) {
            return rec(lft, cl);
        } else {
            return rec(rgt, cr);
        }
    };
    return rec(G, known_d);
}

vector<int> get_path(int a, int b, const vector<int>& par) {
    vector<int> chain_a;
    for (int v = a; v != -1; v = par[v]) {
        chain_a.push_back(v);
    }
    reverse(chain_a.begin(), chain_a.end()); // root to a
    vector<int> chain_b;
    for (int v = b; v != -1; v = par[v]) {
        chain_b.push_back(v);
    }
    reverse(chain_b.begin(), chain_b.end()); // root to b
    int i = 0;
    int ml = min(chain_a.size(), chain_b.size());
    while (i < ml && chain_a[i] == chain_b[i]) ++i;
    int lca_i = i - 1;
    vector<int> path;
    // from a to lca
    for (int j = chain_a.size() - 1; j >= lca_i; --j) {
        path.push_back(chain_a[j]);
    }
    // from lca+1 to b
    for (int j = lca_i + 1; j < (int)chain_b.size(); ++j) {
        path.push_back(chain_b[j]);
    }
    return path;
}

int main() {
    cin >> n;
    if (n == 1) {
        cout << "Y 1" << endl;
        cout << "1" << endl;
        cout.flush();
        return 0;
    }
    parentt.assign(n + 1, -1);
    col.assign(n + 1, -1);
    parts.assign(2, vector<int>());
    parts[0] = {1};
    col[1] = 0;
    parentt[1] = -1;
    vector<vector<int>> layers = {{1}};
    int curr_color = 0;
    bool is_bip = true;
    while (is_bip) {
        vector<int> unv;
        for (int i = 1; i <= n; ++i) {
            if (col[i] == -1) unv.push_back(i);
        }
        if (unv.empty()) break;
        vector<int> F = layers.back();
        int f_col = curr_color;
        int next_col = 1 - f_col;
        vector<int> Same = parts[next_col];
        int e_F = 0; // always
        int e_U = main_query_set(unv);
        vector<int> Fu = F;
        Fu.insert(Fu.end(), unv.begin(), unv.end());
        int e_Fu = main_query_set(Fu);
        long long tot_cross = (long long)e_Fu - e_F - e_U;
        vector<int> cand;
        if (tot_cross > 0) {
            cand = find_all_connected(F, unv, tot_cross, e_F);
        }
        // now cand
        bool conflict = false;
        int conflict_u = -1;
        for (int uu : cand) {
            vector<int> Su = Same;
            Su.push_back(uu);
            int e_Su = main_query_set(Su);
            int d_same = e_Su;
            if (d_same > 0) {
                conflict = true;
                conflict_u = uu;
                // handle non bip
                int s = find_one_neighbor(Same, uu);
                int f = find_one_neighbor(F, uu);
                vector<int> pth = get_path(s, f, parentt);
                vector<int> cyc = pth;
                cyc.push_back(uu);
                cout << "N " << cyc.size() << endl;
                for (int v : cyc) cout << v << " ";
                cout << endl;
                cout.flush();
                return 0;
            }
        }
        if (conflict) continue; // but already handled
        // now check e_L
        int e_L = main_query_set(cand);
        if (e_L > 0) {
            // within conflict
            int ch_u = -1;
            int e_lm = -1;
            vector<int> Lm;
            for (int uu : cand) {
                Lm = cand;
                auto itt = find(Lm.begin(), Lm.end(), uu);
                if (itt != Lm.end()) Lm.erase(itt);
                int elmm = main_query_set(Lm);
                int dd = e_L - elmm;
                if (dd > 0) {
                    ch_u = uu;
                    e_lm = elmm;
                    break;
                }
            }
            assert(ch_u != -1);
            vector<int> GG = Lm; // the L \ ch_u
            int kn_d = e_L - e_lm;
            int u2 = find_one_in_group(ch_u, GG, kn_d);
            int u1 = ch_u;
            int f1 = find_one_neighbor(F, u1);
            int f2 = find_one_neighbor(F, u2);
            vector<int> pth = get_path(f2, f1, parentt);
            vector<int> cyc;
            cyc.push_back(u1);
            cyc.push_back(u2);
            for (int v : pth) cyc.push_back(v);
            cout << "N " << cyc.size() << endl;
            for (int v : cyc) cout << v << " ";
            cout << endl;
            cout.flush();
            return 0;
        }
        // no conflict, add
        for (int uu : cand) {
            int pr = find_one_neighbor(F, uu);
            parentt[uu] = pr;
        }
        layers.push_back(cand);
        parts[next_col].insert(parts[next_col].end(), cand.begin(), cand.end());
        for (int uu : cand) col[uu] = next_col;
        curr_color = next_col;
    }
    // bip
    cout << "Y " << parts[0].size() << endl;
    for (int v : parts[0]) cout << v << " ";
    cout << endl;
    cout.flush();
    return 0;
}