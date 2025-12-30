#include <bits/stdc++.h>
using namespace std;

struct PairInfo {
    int s, l, pos1, pos2;
};

int main() {
    int n;
    scanf("%d", &n);
    vector<int> rem(n);
    for (int i = 0; i < n; i++) rem[i] = i + 1;
    vector<PairInfo> pair_infos;
    int low = 1;
    while (!rem.empty()) {
        int cn = rem.size();
        int m = cn - 1;
        long long total = (long long)(cn / 2) * (n + 1LL);
        long long rr = total % m;
        if (m == 0) rr = 0; // though cn>=2, m>=1
        vector<int> specials;
        for (int ii = 0; ii < cn; ii++) {
            int j = rem[ii];
            printf("? %d", m);
            for (int pp = 0; pp < cn; pp++) {
                if (pp != ii) printf(" %d", rem[pp]);
            }
            printf("\n");
            fflush(stdout);
            int ans;
            scanf("%d", &ans);
            if (ans == 1) {
                specials.push_back(j);
            }
        }
        assert(specials.size() == 2);
        sort(specials.begin(), specials.end());
        int s_val = low;
        int l_val = n + 1 - low;
        pair_infos.push_back({s_val, l_val, specials[0], specials[1]});
        low++;
        vector<int> newrem;
        set<int> spec_set(specials.begin(), specials.end());
        for (int pos : rem) {
            if (spec_set.find(pos) == spec_set.end()) newrem.push_back(pos);
        }
        rem = newrem;
    }
    vector<int> assignment(n + 1, 0);
    int num_pairs = pair_infos.size();
    for (int i = 0; i < num_pairs; i++) {
        PairInfo pi = pair_infos[i];
        int x = pi.pos1;
        int y = pi.pos2;
        int s = pi.s;
        int l = pi.l;
        long long d = (long long)l - s;
        int f = 1;
        int kk = 3;
        while (d % kk == 0) {
            f++;
            kk = 2 * f + 1;
        }
        vector<int> full_pos;
        int chosen = 0;
        for (int jj = 0; chosen < f && jj < num_pairs; jj++) {
            if (jj == i) continue;
            full_pos.push_back(pair_infos[jj].pos1);
            full_pos.push_back(pair_infos[jj].pos2);
            chosen++;
        }
        assert(chosen == f);
        full_pos.push_back(x);
        printf("? %d", kk);
        for (int pos : full_pos) {
            printf(" %d", pos);
        }
        printf("\n");
        fflush(stdout);
        int ans;
        scanf("%d", &ans);
        long long fn1 = (long long)f * (n + 1LL);
        long long sum_s = fn1 + s;
        long long mod_s = (sum_s % kk + kk) % kk;
        bool cond_s = (mod_s == 0);
        long long sum_l = fn1 + l;
        long long mod_l = (sum_l % kk + kk) % kk;
        bool cond_l = (mod_l == 0);
        int pred_s = cond_s ? 1 : 0;
        int pred_l = cond_l ? 1 : 0;
        if (ans == pred_s) {
            assignment[x] = s;
            assignment[y] = l;
        } else {
            assignment[x] = l;
            assignment[y] = s;
        }
    }
    if (assignment[1] > n / 2) {
        for (int i = 1; i <= n; i++) {
            assignment[i] = n + 1 - assignment[i];
        }
    }
    printf("!");
    for (int i = 1; i <= n; i++) {
        printf(" %d", assignment[i]);
    }
    printf("\n");
    fflush(stdout);
    return 0;
}