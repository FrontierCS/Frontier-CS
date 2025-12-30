#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    for (int test = 0; test < t; test++) {
        int n;
        cin >> n;
        vector<int> cur_mask(n + 1, 1); // bit 0 for initial
        while (true) {
            int num_pos = 0;
            long long total_w = 0;
            for (int i = 1; i <= n; i++) {
                int mk = cur_mask[i];
                if (mk) {
                    num_pos++;
                    total_w += __builtin_popcount(mk);
                }
            }
            if (num_pos <= 2) break;
            long long target = total_w / 2;
            long long cum_w = 0;
            int chosen_m = n;
            for (int i = 1; i <= n; i++) {
                int mk = cur_mask[i];
                if (mk) cum_w += __builtin_popcount(mk);
                if (cum_w >= target) {
                    chosen_m = i;
                    break;
                }
            }
            // query [1, chosen_m]
            cout << "? 1 " << chosen_m << endl;
            cout.flush();
            int x;
            cin >> x;
            int len_ = chosen_m;
            int S = (x == len_ - 1) ? 1 : 0;
            vector<int> new_mask(n + 1, 0);
            for (int i = 1; i <= n; i++) {
                int mk = cur_mask[i];
                if (mk == 0) continue;
                int T = (i <= chosen_m) ? 1 : 0;
                int L = S ^ T;
                int temp = 0;
                for (int st = 0; st < 5; st++) {
                    if ((mk & (1 << st)) == 0) continue;
                    bool can = false;
                    int next_st = -1;
                    if (st == 0) {
                        next_st = (L == 0 ? 1 : 3);
                        can = true;
                    } else if (st == 1) {
                        if (L == 0) {
                            next_st = 2;
                            can = true;
                        } else {
                            next_st = 3;
                            can = true;
                        }
                    } else if (st == 2) {
                        if (L == 0) {
                            can = false;
                        } else {
                            next_st = 3;
                            can = true;
                        }
                    } else if (st == 3) {
                        if (L == 0) {
                            next_st = 1;
                            can = true;
                        } else {
                            next_st = 4;
                            can = true;
                        }
                    } else if (st == 4) {
                        if (L == 1) {
                            can = false;
                        } else {
                            next_st = 1;
                            can = true;
                        }
                    }
                    if (can) {
                        temp |= (1 << next_st);
                    }
                }
                if (temp != 0) {
                    new_mask[i] = temp;
                }
            }
            cur_mask = new_mask;
        }
        // now collect candidates
        vector<int> cands;
        for (int i = 1; i <= n; i++) {
            if (cur_mask[i] != 0) {
                cands.push_back(i);
            }
        }
        for (int a : cands) {
            cout << "! " << a << endl;
            cout.flush();
            int y;
            cin >> y;
        }
        cout << "#" << endl;
        cout.flush();
    }
    return 0;
}