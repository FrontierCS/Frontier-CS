#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    if (n == 1) {
        cout << "Y 1" << endl;
        cout << 1 << endl;
        cout.flush();
        return 0;
    }
    vector<int> parent(n + 1, 0);
    vector<int> C = {1};
    vector<int> U;
    for (int i = 2; i <= n; i++) U.push_back(i);
    int e_current = 0;
    auto ask = [&](const vector<int>& s) {
        cout << "? " << s.size() << endl;
        for (size_t i = 0; i < s.size(); i++) {
            cout << s[i];
            if (i + 1 < s.size()) cout << " ";
            else cout << endl;
        }
        cout.flush();
    };
    auto read_int = []() -> int {
        int x;
        cin >> x;
        if (x == -1) exit(0);
        return x;
    };
    for (int i = 1; i < n; i++) {
        vector<int> cands = U;
        while (cands.size() > 1) {
            size_t sz = cands.size();
            size_t hs = sz / 2;
            vector<int> S(cands.begin(), cands.begin() + hs);
            ask(S);
            int es = read_int();
            vector<int> cs = C;
            cs.insert(cs.end(), S.begin(), S.end());
            ask(cs);
            int ms = read_int();
            int cr = ms - e_current - es;
            if (cr > 0) {
                cands.assign(S.begin(), S.end());
            } else {
                cands.erase(cands.begin(), cands.begin() + hs);
            }
        }
        int u = cands[0];
        vector<int> cu = C;
        cu.push_back(u);
        ask(cu);
        int mcu = read_int();
        int degc = mcu - e_current;
        vector<int> scands = C;
        while (scands.size() > 1) {
            size_t sz = scands.size();
            size_t hs = sz / 2;
            vector<int> T(scands.begin(), scands.begin() + hs);
            ask(T);
            int et = read_int();
            vector<int> tu = T;
            tu.push_back(u);
            ask(tu);
            int mtu = read_int();
            int crp = mtu - et;
            if (crp > 0) {
                scands.assign(T.begin(), T.end());
            } else {
                scands.erase(scands.begin(), scands.begin() + hs);
            }
        }
        int p = scands[0];
        parent[u] = p;
        auto posu = find(U.begin(), U.end(), u);
        U.erase(posu);
        C.push_back(u);
        e_current += degc;
    }
    vector<int> col(n + 1, -1);
    function<int(int)> getcol = [&](int v) -> int {
        if (col[v] != -1) return col[v];
        if (v == 1) return col[1] = 0;
        return col[v] = 1 - getcol(parent[v]);
    };
    for (int i = 1; i <= n; i++) getcol(i);
    vector<int> part[2];
    for (int i = 1; i <= n; i++) {
        part[col[i]].push_back(i);
    }
    int m[2] = {0, 0};
    for (int c = 0; c < 2; c++) {
        if (!part[c].empty()) {
            ask(part[c]);
            m[c] = read_int();
        }
    }
    if (m[0] == 0 && m[1] == 0) {
        int s = part[0].size();
        cout << "Y " << s << endl;
        for (size_t i = 0; i < part[0].size(); i++) {
            cout << part[0][i];
            if (i + 1 < part[0].size()) cout << " ";
            else cout << endl;
        }
        cout.flush();
        return 0;
    }
    int conf_c = (m[0] > 0 ? 0 : 1);
    vector<int> samep = part[conf_c];
    int esame = m[conf_c];
    int xx = -1;
    for (int candx : samep) {
        vector<int> withoutc = samep;
        auto itc = find(withoutc.begin(), withoutc.end(), candx);
        withoutc.erase(itc);
        ask(withoutc);
        int ew = read_int();
        int deginc = esome - ew;
        if (deginc > 0) {
            xx = candx;
            break;
        }
    }
    vector<int> aprime = samep;
    auto itxx = find(aprime.begin(), aprime.end(), xx);
    aprime.erase(itxx);
    vector<int> scandy = aprime;
    while (scandy.size() > 1) {
        size_t sz = scandy.size();
        size_t hs = sz / 2;
        vector<int> S(scandy.begin(), scandy.begin() + hs);
        ask(S);
        int es = read_int();
        vector<int> sx = S;
        sx.push_back(xx);
        ask(sx);
        int msx = read_int();
        int cr = msx - es;
        if (cr > 0) {
            scandy.assign(S.begin(), S.end());
        } else {
            scandy.erase(scandy.begin(), scandy.begin() + hs);
        }
    }
    int yy = scandy[0];
    vector<int> fxtr;
    int curx = xx;
    while (curx != 1) {
        fxtr.push_back(curx);
        curx = parent[curx];
    }
    fxtr.push_back(1);
    reverse(fxtr.begin(), fxtr.end());
    vector<int> fytr;
    int cury = yy;
    while (cury != 1) {
        fytr.push_back(cury);
        cury = parent[cury];
    }
    fytr.push_back(1);
    reverse(fytr.begin(), fytr.end());
    size_t lpos = 0;
    size_t mln = min(fxtr.size(), fytr.size());
    for (size_t k = 0; k < mln; k++) {
        if (fxtr[k] != fytr[k]) break;
        lpos = k;
    }
    vector<int> lca_to_x(fxtr.begin() + lpos, fxtr.end());
    vector<int> lca_to_y(fytr.begin() + lpos, fytr.end());
    vector<int> x_to_lca = lca_to_x;
    reverse(x_to_lca.begin(), x_to_lca.end());
    vector<int> tree_path = x_to_lca;
    for (size_t kk = 1; kk < lca_to_y.size(); kk++) {
        tree_path.push_back(lca_to_y[kk]);
    }
    int ll = tree_path.size();
    cout << "N " << ll << endl;
    for (size_t i = 0; i < tree_path.size(); i++) {
        cout << tree_path[i];
        if (i + 1 < tree_path.size()) cout << " ";
        else cout << endl;
    }
    cout.flush();
    return 0;
}