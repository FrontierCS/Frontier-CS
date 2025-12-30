#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    cin >> n;
    string res(n + 1, ' ');
    int c_close = -1;
    int s_end = min(500, n - 1);
    vector<int> S;
    for (int i = 1; i <= s_end; ++i) S.push_back(i);
    int first_tp = s_end + 1;
    int num_tp = min(180, n - s_end);
    int last_tp = first_tp + num_tp - 1;
    int found_close = -1;
    for (int pp = first_tp; pp <= last_tp && pp <= n; ++pp) {
        int m = S.size();
        cout << "0 " << 2 * m;
        for (int ii = 0; ii < m; ++ii) {
            cout << " " << S[ii] << " " << pp;
        }
        cout << endl;
        int f;
        cin >> f;
        if (f > 0) {
            found_close = pp;
            break;
        }
    }
    if (found_close != -1) {
        c_close = found_close;
    } else {
        int assumed_o = first_tp;
        vector<int> cands;
        for (int i = 1; i <= n; ++i) {
            if (i != assumed_o) cands.push_back(i);
        }
        while (cands.size() > 1) {
            int h = cands.size() / 2;
            vector<int> test_h(cands.begin(), cands.begin() + h);
            int mm = test_h.size();
            cout << "0 " << 2 * mm;
            for (int ii = 0; ii < mm; ++ii) {
                cout << " " << assumed_o << " " << test_h[ii];
            }
            cout << endl;
            int ff;
            cin >> ff;
            if (ff > 0) {
                cands = move(test_h);
            } else {
                cands.erase(cands.begin(), cands.begin() + h);
            }
        }
        int cand_c = cands.empty() ? 1 : cands[0];
        cout << "0 2 " << assumed_o << " " << cand_c << endl;
        int fv;
        cin >> fv;
        if (fv == 1) {
            c_close = cand_c;
        } else {
            c_close = 1;
        }
    }
    res[c_close] = ')';
    vector<int> to_test;
    for (int i = 1; i <= n; ++i) {
        if (i != c_close) to_test.push_back(i);
    }
    int nt = to_test.size();
    int gsize = 8;
    int num_g = (nt + gsize - 1) / gsize;
    for (int g = 0; g < num_g; ++g) {
        int st = g * gsize;
        int en = min(st + gsize, nt);
        int sz = en - st;
        vector<int> js(sz);
        for (int ii = 0; ii < sz; ++ii) {
            js[ii] = to_test[st + ii];
        }
        vector<int> qidx;
        for (int kk = 0; kk < sz; ++kk) {
            int w = 1 << kk;
            for (int rep = 0; rep < w; ++rep) {
                qidx.push_back(js[kk]);
                qidx.push_back(c_close);
                qidx.push_back(c_close);
            }
        }
        int kq = qidx.size();
        cout << "0 " << kq;
        for (int idx : qidx) {
            cout << " " << idx;
        }
        cout << endl;
        int f;
        cin >> f;
        for (int kk = 0; kk < sz; ++kk) {
            if (f & (1 << kk)) {
                res[js[kk]] = '(';
            } else {
                res[js[kk]] = ')';
            }
        }
    }
    string out = "";
    for (int i = 1; i <= n; ++i) out += res[i];
    cout << "1 " << out << endl;
    return 0;
}