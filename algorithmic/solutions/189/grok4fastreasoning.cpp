#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    string S1, S2;
    cin >> S1 >> S2;
    int n = S1.length(), m = S2.length();
    vector<int> pos[128];
    for (int j = 0; j < m; j++) {
        pos[(unsigned char)S2[j]].push_back(j);
    }
    vector<int> match_s1, match_s2;
    int ii = 0, jj = 0;
    while (ii < n) {
        unsigned char c = S1[ii];
        auto& p = pos[c];
        auto it = lower_bound(p.begin(), p.end(), jj);
        if (it != p.end()) {
            int jp = *it;
            match_s1.push_back(ii);
            match_s2.push_back(jp);
            jj = jp + 1;
            ii++;
        } else {
            ii++;
        }
    }
    int L = match_s1.size();
    int D_lcs = n + m - 2 * L;
    int mn = min(n, m);
    int mis_left = 0;
    for (int k = 0; k < mn; k++) {
        if (S1[k] != S2[k]) mis_left++;
    }
    int D_left = mis_left + abs(n - m);
    int ol = min(n, m);
    int mis_right = 0;
    for (int k = 0; k < ol; k++) {
        if (S1[n - 1 - k] != S2[m - 1 - k]) mis_right++;
    }
    int D_right = mis_right + abs(n - m);
    int minD = min({D_left, D_right, D_lcs});
    string T;
    if (minD == D_left) {
        T = "";
        for (int k = 0; k < mn; k++) {
            T += 'M';
        }
        if (n > m) {
            for (int k = 0; k < n - m; k++) T += 'D';
        } else {
            for (int k = 0; k < m - n; k++) T += 'I';
        }
    } else if (minD == D_right) {
        T = "";
        int extra = abs(n - m);
        if (n <= m) {
            for (int k = 0; k < extra; k++) T += 'I';
            for (int k = 0; k < n; k++) T += 'M';
        } else {
            for (int k = 0; k < extra; k++) T += 'D';
            for (int k = 0; k < m; k++) T += 'M';
        }
    } else {
        T = "";
        int k = 0;
        int cur_i = 0, cur_j = 0;
        int num_matches = match_s1.size();
        while (k < num_matches) {
            while (cur_i < match_s1[k]) {
                T += 'D';
                cur_i++;
            }
            while (cur_j < match_s2[k]) {
                T += 'I';
                cur_j++;
            }
            T += 'M';
            cur_i++;
            cur_j++;
            k++;
        }
        while (cur_i < n) {
            T += 'D';
            cur_i++;
        }
        while (cur_j < m) {
            T += 'I';
            cur_j++;
        }
    }
    cout << T << endl;
    return 0;
}