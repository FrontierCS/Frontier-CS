#include <bits/stdc++.h>
using namespace std;

int edit_dist(const string& a, int ai, int alen, const string& b, int bi, int blen) {
    if (alen == 0) return blen;
    if (blen == 0) return alen;
    const int MAXL = 11;
    char prev[MAXL];
    char curr[MAXL];
    for (int jj = 0; jj <= blen; ++jj) {
        prev[jj] = jj;
    }
    for (int ii = 1; ii <= alen; ++ii) {
        curr[0] = ii;
        for (int jj = 1; jj <= blen; ++jj) {
            char cost = (a[ai + ii - 1] == b[bi + jj - 1] ? 0 : 1);
            char subst = prev[jj - 1] + cost;
            char dele = prev[jj] + 1;
            char inse = curr[jj - 1] + 1;
            curr[jj] = min({subst, dele, inse});
        }
        memcpy(prev, curr, (blen + 1) * sizeof(char));
    }
    return prev[blen];
}

int main() {
    string s1, s2;
    cin >> s1 >> s2;
    int n = s1.size();
    int m = s2.size();
    string t = "";
    int i = 0, j = 0;
    const int W = 10;
    while (i < n || j < m) {
        if (i >= n) {
            t += 'I';
            ++j;
            continue;
        }
        if (j >= m) {
            t += 'D';
            ++i;
            continue;
        }
        if (s1[i] == s2[j]) {
            t += 'M';
            ++i;
            ++j;
            continue;
        }
        // mismatch
        struct Option {
            int score;
            int diff;
            int type;
        };
        vector<Option> opts(3);
        // sub
        {
            int si2 = i + 1, sj2 = j + 1;
            int ll1 = min(W, n - si2);
            int ll2 = min(W, m - sj2);
            int ed = edit_dist(s1, si2, ll1, s2, sj2, ll2);
            int la_km = ll1 + ll2 - ed;
            int cur_km = 1;
            int total_km = cur_km + la_km;
            opts[0] = {total_km, abs(ll1 - ll2), 0};
        }
        // del
        {
            int si2 = i + 1, sj2 = j;
            int ll1 = min(W, n - si2);
            int ll2 = min(W, m - sj2);
            int ed = edit_dist(s1, si2, ll1, s2, sj2, ll2);
            int la_km = ll1 + ll2 - ed;
            int cur_km = 0;
            int total_km = cur_km + la_km;
            opts[1] = {total_km, abs(ll1 - ll2), 1};
        }
        // ins
        {
            int si2 = i, sj2 = j + 1;
            int ll1 = min(W, n - si2);
            int ll2 = min(W, m - sj2);
            int ed = edit_dist(s1, si2, ll1, s2, sj2, ll2);
            int la_km = ll1 + ll2 - ed;
            int cur_km = 0;
            int total_km = cur_km + la_km;
            opts[2] = {total_km, abs(ll1 - ll2), 2};
        }
        // find best
        int max_s = -1;
        for (int k = 0; k < 3; ++k) {
            max_s = max(max_s, opts[k].score);
        }
        vector<int> candidates;
        for (int k = 0; k < 3; ++k) {
            if (opts[k].score == max_s) {
                candidates.push_back(k);
            }
        }
        int best_type = -1;
        if (candidates.size() == 1) {
            best_type = candidates[0];
        } else {
            int min_d = INT_MAX;
            for (int k : candidates) {
                min_d = min(min_d, opts[k].diff);
            }
            vector<int> cand2;
            for (int k : candidates) {
                if (opts[k].diff == min_d) {
                    cand2.push_back(k);
                }
            }
            sort(cand2.begin(), cand2.end());
            best_type = cand2[0];
        }
        if (best_type == 0) {
            t += 'M';
            ++i;
            ++j;
        } else if (best_type == 1) {
            t += 'D';
            ++i;
        } else {
            t += 'I';
            ++j;
        }
    }
    cout << t << endl;
    return 0;
}