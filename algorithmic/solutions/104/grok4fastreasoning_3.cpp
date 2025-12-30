#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int t;
    cin >> t;
    const int N = 100005;
    bool poss[N];
    int last_choice[N];
    int run_len[N];
    for (int test = 0; test < t; test++) {
        int n;
        cin >> n;
        int total = n;
        for (int i = 1; i <= n; i++) {
            poss[i] = true;
            run_len[i] = 0;
        }
        double l1 = log(static_cast<double>(n));
        double l2 = log(1.116);
        int ce = static_cast<int>(ceil(l1 / l2));
        int maxq = 2 * ce;
        int qcount = 0;
        while (total > 2 && qcount < maxq) {
            int target = total / 2;
            if (target == 0) target = 1;
            int cum = 0;
            int m = n;
            for (int i = 1; i <= n; i++) {
                if (poss[i]) cum++;
                if (cum >= target) {
                    m = i;
                    break;
                }
            }
            cout << "? 1 " << m << endl;
            cout.flush();
            int x;
            cin >> x;
            qcount++;
            int len_ = m;
            int true_in = len_ - 1;
            int true_out = len_;
            int new_total = 0;
            for (int i = 1; i <= n; i++) {
                if (!poss[i]) continue;
                int t = (i <= m ? true_in : true_out);
                bool is_honest = (x == t);
                int new_choice = is_honest ? 0 : 1;
                bool survives = true;
                int new_r;
                if (run_len[i] == 0) {
                    new_r = 1;
                } else {
                    int prev_c = last_choice[i];
                    if (new_choice == prev_c) {
                        new_r = run_len[i] + 1;
                        if (new_r > 2) survives = false;
                    } else {
                        new_r = 1;
                    }
                }
                if (survives) {
                    last_choice[i] = new_choice;
                    run_len[i] = new_r;
                    new_total++;
                } else {
                    poss[i] = false;
                }
            }
            total = new_total;
        }
        vector<int> candidates;
        for (int i = 1; i <= n; i++) {
            if (poss[i]) candidates.push_back(i);
        }
        for (int cand : candidates) {
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