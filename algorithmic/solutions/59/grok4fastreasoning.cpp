#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> a(n + 1);
    set<int> unu;
    for (int i = 1; i <= n; ++i) unu.insert(i);
    int cur = 1;
    while (cur <= n) {
        if (cur == n) {
            a[n] = *unu.begin();
            unu.erase(a[n]);
            ++cur;
            continue;
        }
        if (cur == n - 1) {
            // remaining 2
            auto it = unu.begin();
            int p = *it; ++it;
            int q = *it;
            cout << "? " << cur << " " << (cur + 1) << endl;
            cout.flush();
            char sgn;
            cin >> sgn;
            if (sgn == '<') {
                a[cur] = p;
                a[cur + 1] = q;
            } else {
                a[cur] = q;
                a[cur + 1] = p;
            }
            unu.erase(p);
            unu.erase(q);
            cur = n + 1;
            continue;
        }
        // full group cur, cur+1, cur+2
        // get cands
        vector<int> cands;
        auto it = unu.lower_bound(1);
        while (it != unu.end() && *it <= cur + 2) {
            cands.push_back(*it);
            ++it;
        }
        assert(cands.size() == 3);
        int pp = cands[0], qq = cands[1], rr = cands[2];
        // queries
        vector<pair<int, int>> qpairs = {{cur, cur + 1}, {cur + 1, cur + 2}, {cur, cur + 2}};
        vector<char> signs(3);
        for (int qi = 0; qi < 3; ++qi) {
            int x = qpairs[qi].first, y = qpairs[qi].second;
            cout << "? " << x << " " << y << endl;
            cout.flush();
            cin >> signs[qi];
        }
        // compute rank[0,1,2] for local pos 0=cur,1=cur+1,2=cur+2
        int cm[3][3] = {};
        // 0-1
        if (signs[0] == '<') {
            cm[0][1] = -1; cm[1][0] = 1;
        } else {
            cm[0][1] = 1; cm[1][0] = -1;
        }
        // 1-2
        if (signs[1] == '<') {
            cm[1][2] = -1; cm[2][1] = 1;
        } else {
            cm[1][2] = 1; cm[2][1] = -1;
        }
        // 0-2
        if (signs[2] == '<') {
            cm[0][2] = -1; cm[2][0] = 1;
        } else {
            cm[0][2] = 1; cm[2][0] = -1;
        }
        vector<int> rankk(3);
        for (int po = 0; po < 3; ++po) {
            int cnt = 0;
            for (int o = 0; o < 3; ++o) {
                if (o != po && cm[po][o] < 0) ++cnt;
            }
            rankk[po] = cnt;
        }
        // now simulation
        vector<int> best_assign;
        bool found = false;
        int maxs[3];
        maxs[0] = min(2, n - cur);
        maxs[1] = min(2, n - (cur + 1));
        maxs[2] = min(2, n - (cur + 2));
        for (int ini = 0; ini < 2; ++ini) {
            int sm1 = (ini == 0 ? pp : qq);
            int sm2 = (ini == 0 ? qq : pp);
            vector<int> temp0(6, 0);
            temp0[1] = sm1;
            temp0[2] = sm2;
            temp0[3] = rr;
            if (cur + 3 <= n) temp0[4] = cur + 3;
            if (cur + 4 <= n) temp0[5] = cur + 4;
            for (int s0 = 0; s0 <= maxs[0]; ++s0) {
                int j0 = 1 + s0;
                if (j0 > 5) continue;
                if (j0 == 4 && temp0[4] == 0) continue;
                if (j0 == 5 && temp0[5] == 0) continue;
                vector<int> temp1 = temp0;
                swap(temp1[1], temp1[j0]);
                for (int s1 = 0; s1 <= maxs[1]; ++s1) {
                    int j1 = 2 + s1;
                    if (j1 > 5) continue;
                    if (j1 == 4 && temp1[4] == 0) continue;
                    if (j1 == 5 && temp1[5] == 0) continue;
                    vector<int> temp2 = temp1;
                    swap(temp2[2], temp2[j1]);
                    for (int s2 = 0; s2 <= maxs[2]; ++s2) {
                        int j2 = 3 + s2;
                        if (j2 > 5) continue;
                        if (j2 == 4 && temp2[4] == 0) continue;
                        if (j2 == 5 && temp2[5] == 0) continue;
                        vector<int> temp3 = temp2;
                        swap(temp3[3], temp3[j2]);
                        int vval1 = temp3[1];
                        int vval2 = temp3[2];
                        int vval3 = temp3[3];
                        if (vval1 == 0 || vval2 == 0 || vval3 == 0) continue;
                        // compute local cm
                        int lcm[3][3] = {};
                        lcm[0][1] = (vval1 < vval2 ? -1 : 1);
                        lcm[1][0] = -lcm[0][1];
                        lcm[0][2] = (vval1 < vval3 ? -1 : 1);
                        lcm[2][0] = -lcm[0][2];
                        lcm[1][2] = (vval2 < vval3 ? -1 : 1);
                        lcm[2][1] = -lcm[1][2];
                        // local rank
                        vector<int> lrank(3);
                        for (int po = 0; po < 3; ++po) {
                            int cnt = 0;
                            for (int o = 0; o < 3; ++o) {
                                if (o != po && lcm[po][o] < 0) ++cnt;
                            }
                            lrank[po] = cnt;
                        }
                        // check match
                        bool mat = (lrank[0] == rankk[0] && lrank[1] == rankk[1] && lrank[2] == rankk[2]);
                        if (mat) {
                            vector<int> this_assign = {vval1, vval2, vval3};
                            if (!found) {
                                best_assign = this_assign;
                                found = true;
                            } else if (best_assign != this_assign) {
                                // ambiguity, but assume not
                                assert(false);
                            }
                        }
                    }
                }
            }
        }
        assert(found);
        a[cur] = best_assign[0];
        a[cur + 1] = best_assign[1];
        a[cur + 2] = best_assign[2];
        unu.erase(a[cur]);
        unu.erase(a[cur + 1]);
        unu.erase(a[cur + 2]);
        cur += 3;
    }
    // output
    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << a[i];
    }
    cout << endl;
    cout.flush();
    return 0;
}