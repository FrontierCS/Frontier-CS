#include <bits/stdc++.h>
using namespace std;

bool is_valid(const vector<int>& e) {
    int m = e.size();
    if (m == 0) return true;
    int cons = 1;
    for (int j = 1; j < m; j++) {
        if (e[j] == e[j - 1]) {
            cons++;
            if (cons >= 3) return false;
        } else {
            cons = 1;
        }
    }
    return true;
}

int main() {
    int t;
    cin >> t;
    for (int test = 0; test < t; test++) {
        int n;
        cin >> n;
        int low = 1, high = n;
        vector<pair<int, int>> queries;
        vector<int> resps;
        while (low < high) {
            int mid = low + (high - low) / 2;
            cout << "? " << low << " " << mid << endl;
            cout.flush();
            int x;
            cin >> x;
            int len = mid - low + 1;
            int bp = (x == len - 1 ? 1 : 0);
            queries.emplace_back(low, mid);
            resps.push_back(bp);
            if (bp == 1) {
                high = mid;
            } else {
                low = mid + 1;
            }
        }
        vector<int> poss_k;
        for (int k = 1; k <= n; k++) {
            vector<int> e(queries.size());
            for (size_t i = 0; i < queries.size(); i++) {
                auto [li, ri] = queries[i];
                int b = (li <= k && k <= ri ? 1 : 0);
                e[i] = b ^ resps[i];
            }
            if (is_valid(e)) {
                poss_k.push_back(k);
            }
        }
        vector<int> curr_k = poss_k;
        vector<int> curr_st(curr_k.size(), -1);
        bool need_states = (curr_k.size() > 2);
        if (need_states) {
            for (size_t j = 0; j < curr_k.size(); j++) {
                int k = curr_k[j];
                vector<int> e(queries.size());
                for (size_t i = 0; i < queries.size(); i++) {
                    auto [li, ri] = queries[i];
                    int b = (li <= k && k <= ri ? 1 : 0);
                    e[i] = b ^ resps[i];
                }
                int ctype = -1;
                int cstrk = 0;
                for (int ei : e) {
                    if (cstrk == 0) {
                        ctype = ei;
                        cstrk = 1;
                    } else if (ei == ctype) {
                        cstrk++;
                    } else {
                        ctype = ei;
                        cstrk = 1;
                    }
                }
                int st;
                if (ctype == 0) {
                    st = (cstrk == 1 ? 0 : 1);
                } else {
                    st = (cstrk == 1 ? 2 : 3);
                }
                curr_st[j] = st;
            }
            int ms = curr_k.size();
            while (ms > 2) {
                vector<int> ord(ms);
                iota(ord.begin(), ord.end(), 0);
                sort(ord.begin(), ord.end(), [&](int a, int b) {
                    return curr_k[a] < curr_k[b];
                });
                int hlf = ms / 2;
                if (hlf == 0) break;
                int sidx = hlf - 1;
                int sp = ord[sidx];
                int splt = curr_k[sp];
                int minp = curr_k[ord[0]];
                int ql = minp;
                int qr = splt;
                cout << "? " << ql << " " << qr << endl;
                cout.flush();
                int xx;
                cin >> xx;
                int lenx = qr - ql + 1;
                int bpnew = (xx == lenx - 1 ? 1 : 0);
                vector<int> newk, newst;
                for (int ii = 0; ii < ms; ii++) {
                    int kk = curr_k[ii];
                    int btrue = (ql <= kk && kk <= qr ? 1 : 0);
                    int enew = btrue ^ bpnew;
                    int ost = curr_st[ii];
                    int ctype, cstrk;
                    if (ost == 0) {
                        ctype = 0;
                        cstrk = 1;
                    } else if (ost == 1) {
                        ctype = 0;
                        cstrk = 2;
                    } else if (ost == 2) {
                        ctype = 1;
                        cstrk = 1;
                    } else {
                        ctype = 1;
                        cstrk = 2;
                    }
                    bool can = true;
                    int ntype = enew;
                    int nstrk;
                    if (enew == ctype) {
                        nstrk = cstrk + 1;
                        if (nstrk > 2) can = false;
                    } else {
                        nstrk = 1;
                    }
                    if (can) {
                        int nst;
                        if (ntype == 0) {
                            nst = (nstrk == 1 ? 0 : 1);
                        } else {
                            nst = (nstrk == 1 ? 2 : 3);
                        }
                        newk.push_back(kk);
                        newst.push_back(nst);
                    }
                }
                curr_k = std::move(newk);
                curr_st = std::move(newst);
                ms = curr_k.size();
            }
        }
        for (int kk : curr_k) {
            cout << "! " << kk << endl;
            cout.flush();
            int yy;
            cin >> yy;
        }
        if (curr_k.empty()) {
            cout << "! " << low << endl;
            cout.flush();
            int dummy;
            cin >> dummy;
        }
        cout << "#" << endl;
        cout.flush();
    }
    return 0;
}