#include <bits/stdc++.h>
using namespace std;

long long queryy(const vector<int>& s) {
    int k = s.size();
    if (k == 0) return 0;
    cout << "? " << k << endl;
    for (int v : s) cout << v << " ";
    cout << endl;
    cout.flush();
    long long m;
    cin >> m;
    if (m == -1) exit(0);
    return m;
}

int find_one_adj(int u, const vector<int>& pset) {
    vector<int> temp = pset;
    while (temp.size() > 1) {
        size_t h = temp.size() / 2;
        vector<int> left(temp.begin(), temp.begin() + h);
        vector<int> qul;
        qul.push_back(u);
        qul.insert(qul.end(), left.begin(), left.end());
        long long eql = queryy(qul);
        if (eql > 0) {
            temp = left;
        } else {
            vector<int> right(temp.begin() + h, temp.end());
            temp = right;
        }
    }
    return temp[0];
}

int find_one_connected(const vector<int>& cand_in, const vector<int>& processed, long long ep) {
    vector<int> temp = cand_in;
    while (temp.size() > 1) {
        size_t h = temp.size() / 2;
        vector<int> left(temp.begin(), temp.begin() + h);
        long long e_t = queryy(left);
        vector<int> tp = left;
        tp.insert(tp.end(), processed.begin(), processed.end());
        long long e_tp = queryy(tp);
        long long edges_b = e_tp - e_t - ep;
        if (edges_b > 0) {
            temp = left;
        } else {
            vector<int> right(temp.begin() + h, temp.end());
            temp = right;
        }
    }
    return temp[0];
}

int main() {
    int n;
    cin >> n;
    if (n == 1) {
        cout << "Y 1" << endl;
        cout << "1" << endl;
        cout.flush();
        return 0;
    }
    vector<int> cand;
    for (int i = 2; i <= n; ++i) cand.push_back(i);
    vector<int> processed = {1};
    vector<int> p_zero = {1};
    vector<int> p_one;
    vector<int> par_arr(n + 1, 0);
    vector<int> color_arr(n + 1, -1);
    vector<int> dep_arr(n + 1, 0);
    color_arr[1] = 0;
    dep_arr[1] = 0;
    long long ep = 0;
    auto get_path = [&](int x) -> vector<int> {
        vector<int> p;
        int cur = x;
        while (cur != 0) {
            p.push_back(cur);
            cur = par_arr[cur];
        }
        reverse(p.begin(), p.end());
        return p;
    };
    while (!cand.empty()) {
        int u = find_one_connected(cand, processed, ep);
        vector<int> u_p0 = p_zero;
        u_p0.push_back(u);
        long long num0 = queryy(u_p0);
        vector<int> u_p1 = p_one;
        u_p1.push_back(u);
        long long num1 = queryy(u_p1);
        if (num0 > 0 && num1 > 0) {
            // conflict
            int a = find_one_adj(u, p_zero);
            int b = find_one_adj(u, p_one);
            auto patha = get_path(a);
            auto pathb = get_path(b);
            size_t ii = 0;
            size_t lenn = min(patha.size(), pathb.size());
            while (ii < lenn && patha[ii] == pathb[ii]) ++ii;
            size_t lca_idxx = ii ? ii - 1 : 0;
            // a_to_lca
            vector<int> a_to_lca;
            for (size_t j = patha.size() - 1; j >= lca_idxx; --j) {
                a_to_lca.push_back(patha[j]);
            }
            // lca_to_b
            vector<int> lca_to_b;
            for (size_t j = lca_idxx; j < pathb.size(); ++j) {
                lca_to_b.push_back(pathb[j]);
            }
            // cycle
            vector<int> cycle_vec;
            cycle_vec.push_back(u);
            for (int v : a_to_lca) {
                cycle_vec.push_back(v);
            }
            for (size_t j = 1; j < lca_to_b.size(); ++j) {
                cycle_vec.push_back(lca_to_b[j]);
            }
            cout << "N " << cycle_vec.size() << endl;
            for (size_t i = 0; i < cycle_vec.size(); ++i) {
                cout << cycle_vec[i];
                if (i + 1 < cycle_vec.size()) cout << " ";
            }
            cout << endl;
            cout.flush();
            return 0;
        } else {
            int col;
            vector<int> connect_set;
            long long num_connect;
            if (num0 > 0) {
                col = 1;
                connect_set = p_zero;
                num_connect = num0;
            } else {
                col = 0;
                connect_set = p_one;
                num_connect = num1;
            }
            int par = find_one_adj(u, connect_set);
            par_arr[u] = par;
            dep_arr[u] = dep_arr[par] + 1;
            color_arr[u] = col;
            long long total_conn = num0 + num1;
            ep += total_conn;
            if (col == 0) {
                p_zero.push_back(u);
            } else {
                p_one.push_back(u);
            }
            processed.push_back(u);
            auto it = find(cand.begin(), cand.end(), u);
            if (it != cand.end()) {
                cand.erase(it);
            }
        }
    }
    // bipartite
    vector<int> part;
    for (int i = 1; i <= n; ++i) {
        if (color_arr[i] == 0) part.push_back(i);
    }
    cout << "Y " << part.size() << endl;
    for (size_t i = 0; i < part.size(); ++i) {
        cout << part[i];
        if (i + 1 < part.size()) cout << " ";
    }
    cout << endl;
    cout.flush();
    return 0;
}