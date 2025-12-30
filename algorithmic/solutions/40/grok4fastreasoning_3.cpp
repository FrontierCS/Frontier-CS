#include <bits/stdc++.h>
using namespace std;

int ask(const vector<int>& inds) {
    cout << "0 " << inds.size();
    for (int ii : inds) {
        cout << " " << ii;
    }
    cout << endl;
    cout.flush();
    int ff;
    cin >> ff;
    return ff;
}

vector<int> get_indices(int fixed, const vector<int>& js) {
    vector<int> ind;
    ind.push_back(fixed);
    for (int jj : js) {
        ind.push_back(jj);
        ind.push_back(fixed);
    }
    return ind;
}

int find_opposite(int fixed, vector<int> cands) {
    while (cands.size() > 1) {
        int half = cands.size() / 2;
        vector<int> left(cands.begin(), cands.begin() + half);
        vector<int> right(cands.begin() + half, cands.end());
        int fl = ask(get_indices(fixed, left));
        if (fl > 0) {
            cands = left;
        } else {
            cands = right;
        }
    }
    return cands[0];
}

int main() {
    int n;
    cin >> n;
    int fixed = 1;
    vector<int> js;
    int maxm = min(499, n - 1);
    for (int t = 2; t <= 1 + maxm; t++) {
        js.push_back(t);
    }
    int f0 = ask(get_indices(fixed, js));
    int open_p, close_p;
    int opp_j;
    if (f0 > 0) {
        opp_j = find_opposite(fixed, js);
    } else {
        int cur_start = 502; // 1 + 500 +1 ? Wait, initial block 1 to 1+maxm , maxm=499 ->1 to 500
        // cur_start = 501
        bool foundd = false;
        int cur_s = 501;
        while (cur_s <= n && !foundd) {
            int mm = min(499, n - cur_s + 1);
            vector<int> temp_js;
            for (int t = 0; t < mm; t++) {
                temp_js.push_back(cur_s + t);
            }
            int f_temp = ask(get_indices(fixed, temp_js));
            if (f_temp > 0) {
                opp_j = find_opposite(fixed, temp_js);
                foundd = true;
            } else {
                cur_s += mm;
            }
        }
    }
    // now opp_j
    vector<int> pairi = {fixed, opp_j};
    int fs = ask(pairi);
    if (fs == 1) {
        open_p = fixed;
        close_p = opp_j;
    } else {
        open_p = opp_j;
        close_p = fixed;
    }
    // now groups
    string ss(n + 1, '?');
    ss[open_p] = '(';
    ss[close_p] = ')';
    vector<int> unks;
    for (int i = 1; i <= n; i++) {
        if (i != open_p && i != close_p) {
            unks.push_back(i);
        }
    }
    int idx = 0;
    while (idx < (int)unks.size()) {
        int gsize = min(8, (int)unks.size() - idx);
        vector<int> group;
        for (int gg = 0; gg < gsize; gg++) {
            group.push_back(unks[idx + gg]);
        }
        vector<int> wws(gsize);
        for (int r = 0; r < gsize; r++) {
            wws[r] = (1 << r);
        }
        vector<int> qinds;
        for (int r = 0; r < gsize; r++) {
            int ki = group[r];
            int ww = wws[r];
            qinds.push_back(ki);
            qinds.push_back(close_p);
            for (int t = 1; t < ww; t++) {
                qinds.push_back(close_p);
                qinds.push_back(ki);
                qinds.push_back(close_p);
            }
            if (r < gsize - 1) {
                qinds.push_back(close_p);
            }
        }
        int ff = ask(qinds);
        for (int r = 0; r < gsize; r++) {
            if (ff & (1 << r)) {
                ss[group[r]] = '(';
            } else {
                ss[group[r]] = ')';
            }
        }
        idx += gsize;
    }
    // output
    cout << "1";
    for (int i = 1; i <= n; i++) {
        cout << ss[i];
    }
    cout << endl;
    cout.flush();
    return 0;
}