#include <bits/stdc++.h>
using namespace std;

pair<bool, int> get_transition(int st, int f) {
    int last_f = (st < 2 ? 0 : 1);
    int curr_run = ((st % 2) == 1 ? 2 : 1);
    if (f != last_f) {
        int new_st = (f == 0 ? 0 : 2);
        return {true, new_st};
    } else {
        if (curr_run == 2) return {false, -1};
        int new_st = (f == 0 ? 1 : 3);
        return {true, new_st};
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    for (int cas = 0; cas < t; cas++) {
        int n;
        cin >> n;
        double lgn = log((double)n);
        double lb = log(1.116);
        int ck = (int)ceil(lgn / lb);
        int maxq = 2 * ck;
        bitset<100001> bs[4];
        for (int i = 0; i < 4; i++) bs[i].reset();
        // First query
        int fm = n / 2;
        if (fm < 1) fm = 1;
        cout << "? 1 " << fm << endl;
        cout.flush();
        int x;
        cin >> x;
        int len1 = fm;
        int d1 = len1 - x;
        bitset<100001> in_S;
        in_S.reset();
        for (int i = 1; i <= fm; i++) in_S.set(i);
        bitset<100001> out_S;
        out_S.reset();
        for (int i = fm + 1; i <= n; i++) out_S.set(i);
        int f_in1 = 1 ^ d1;
        int newst_in = (f_in1 == 0 ? 0 : 2);
        bs[newst_in] |= in_S;
        int f_out1 = d1;
        int newst_out = (f_out1 == 0 ? 0 : 2);
        bs[newst_out] |= out_S;
        int qcount = 1;
        // Now loop
        while (true) {
            int tot = 0;
            for (int st = 0; st < 4; st++) tot += (int)bs[st].count();
            if (tot <= 2) break;
            if (qcount >= maxq) break;
            // Collect poss
            vector<int> poss;
            for (int i = 1; i <= n; i++) {
                bool isposs = false;
                for (int st = 0; st < 4; st++) {
                    if (bs[st].test(i)) {
                        isposs = true;
                        break;
                    }
                }
                if (isposs) poss.push_back(i);
            }
            int ps = poss.size();
            if (ps <= 2) break;
            int idx = (ps - 1) / 2;
            int m = poss[idx];
            // Query
            cout << "? 1 " << m << endl;
            cout.flush();
            int xx;
            cin >> xx;
            int lenn = m;
            int dd = lenn - xx;
            qcount++;
            // Update
            bitset<100001> rangeb;
            rangeb.reset();
            for (int i = 1; i <= m; i++) rangeb.set(i);
            bitset<100001> newb[4];
            for (int i = 0; i < 4; i++) newb[i].reset();
            for (int prev = 0; prev < 4; prev++) {
                bitset<100001> S = bs[prev];
                if (S.none()) continue;
                bitset<100001> inS = S & rangeb;
                bitset<100001> outS = S & (~rangeb);
                int fin = 1 ^ dd;
                auto [canin, nstin] = get_transition(prev, fin);
                if (canin && inS.any()) {
                    newb[nstin] |= inS;
                }
                int fout = dd;
                auto [canout, nstout] = get_transition(prev, fout);
                if (canout && outS.any()) {
                    newb[nstout] |= outS;
                }
            }
            for (int i = 0; i < 4; i++) bs[i] = newb[i];
        }
        // Collect candidates
        vector<int> cands;
        for (int i = 1; i <= n; i++) {
            bool is = false;
            for (int st = 0; st < 4; st++) {
                if (bs[st].test(i)) {
                    is = true;
                    break;
                }
            }
            if (is) cands.push_back(i);
        }
        // Mark
        for (int cand : cands) {
            cout << "! " << cand << endl;
            cout.flush();
            int y;
            cin >> y;
        }
        cout << "#" << endl;
        cout.flush();
    }
    return 0;
}