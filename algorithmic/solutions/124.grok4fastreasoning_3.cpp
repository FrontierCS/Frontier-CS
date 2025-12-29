#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    scanf("%d", &n);
    vector<int> parity(n + 1, -1);
    parity[1] = 0;
    for (int i = 2; i <= n; ++i) {
        printf("? 2 1 %d\n", i);
        fflush(stdout);
        int res;
        scanf("%d", &res);
        parity[i] = (res == 1 ? 0 : 1);
    }
    vector<int> current;
    for (int i = 1; i <= n; ++i) current.push_back(i);
    vector<pair<int, int>> pos_pairs(n / 2 + 1);
    long long cur_sum = (long long) n * (n + 1) / 2;
    for (int l = 1; l <= n / 2; ++l) {
        int mm = current.size();
        int modd = mm - 1;
        vector<int> specials;
        for (int idx = 0; idx < mm; ++idx) {
            int ipos = current[idx];
            printf("? %d", modd);
            for (int j = 0; j < mm; ++j) {
                if (j != idx) {
                    printf(" %d", current[j]);
                }
            }
            printf("\n");
            fflush(stdout);
            int res;
            scanf("%d", &res);
            if (res == 1) {
                specials.push_back(ipos);
            }
        }
        assert(specials.size() == 2);
        pos_pairs[l] = {specials[0], specials[1]};
        // remove from current
        vector<int> new_current;
        for (int p : current) {
            if (p != specials[0] && p != specials[1]) {
                new_current.push_back(p);
            }
        }
        current = new_current;
        cur_sum -= (l + (n + 1 - l));
    }
    // now assign
    vector<int> perm(n + 1);
    bool assume_zero_odd = true;
    int assumed_rel0_par = assume_zero_odd ? 1 : 0; // 1 odd
    for (int l = 1; l <= n / 2; ++l) {
        int pos1 = pos_pairs[l].first;
        int pos2 = pos_pairs[l].second;
        int val_odd = (l % 2 == 1 ? l : n + 1 - l);
        int val_even = (l % 2 == 1 ? n + 1 - l : l);
        int rel1 = parity[pos1];
        int rel2 = parity[pos2];
        int par1 = (rel1 == 0 ? assumed_rel0_par : 1 - assumed_rel0_par);
        int par2 = (rel2 == 0 ? assumed_rel0_par : 1 - assumed_rel0_par);
        if (par1 == 1) {
            perm[pos1] = val_odd;
            perm[pos2] = val_even;
        } else {
            perm[pos1] = val_even;
            perm[pos2] = val_odd;
        }
    }
    if (perm[1] > n / 2) {
        for (int k = 1; k <= n; ++k) {
            perm[k] = n + 1 - perm[k];
        }
    }
    printf("! ");
    for (int k = 1; k <= n; ++k) {
        printf("%d ", perm[k]);
    }
    printf("\n");
    fflush(stdout);
    return 0;
}