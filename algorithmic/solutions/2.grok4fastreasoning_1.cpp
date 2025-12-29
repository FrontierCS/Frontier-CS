#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    scanf("%d", &n);
    if (n == 1) {
        printf("1 1\n");
        fflush(stdout);
        return 0;
    }
    auto ask = [&](const vector<int>& qq) -> int {
        printf("0");
        for (int i = 1; i <= n; ++i) {
            printf(" %d", qq[i]);
        }
        printf("\n");
        fflush(stdout);
        int x;
        scanf("%d", &x);
        return x;
    };
    vector<int> s(n + 1);
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    bool found = false;
    int attempts = 0;
    while (!found && attempts < 30) {
        vector<int> q(n + 1);
        for (int i = 1; i <= n; ++i) q[i] = i;
        shuffle(q.begin() + 1, q.begin() + n + 1, rng);
        int x = ask(q);
        if (x == 0) {
            s = q;
            found = true;
        }
        ++attempts;
    }
    assert(found);
    vector<int> signature(n + 1, 0);
    for (int kk = 1; kk <= n; ++kk) {
        int bits = 0;
        for (int b = 0; b < 9; ++b) {
            vector<int> qq(n + 1);
            for (int i = 1; i <= n; ++i) qq[i] = s[i];
            for (int i = 1; i <= n; ++i) {
                if (((i - 1) & (1 << b)) != 0) {
                    qq[i] = kk;
                }
            }
            int x = ask(qq);
            if (x != 0) {
                bits |= (1 << b);
            }
        }
        signature[kk] = bits;
    }
    vector<vector<int>> groups(512);
    for (int kk = 1; kk <= n; ++kk) {
        int r = signature[kk];
        groups[r].push_back(kk);
    }
    vector<int> perm(n + 1);
    for (int r = 0; r < 512; ++r) {
        auto& ks = groups[r];
        if (ks.empty()) continue;
        vector<int> poss;
        int base_val = r;
        for (int k = 0;; ++k) {
            int ii = base_val + 1 + 512 * k;
            if (ii > n) break;
            poss.push_back(ii);
        }
        int num = ks.size();
        assert((int)poss.size() == num);
        if (num == 1) {
            int i = poss[0];
            int kk = ks[0];
            perm[i] = kk;
        } else {
            int i1 = poss[0];
            int i2 = poss[1];
            int k1 = ks[0];
            int k2 = ks[1];
            if (k1 > k2) swap(k1, k2);
            vector<int> qq(n + 1);
            for (int j = 1; j <= n; ++j) qq[j] = s[j];
            qq[i1] = k1;
            int x = ask(qq);
            if (x == 1) {
                perm[i1] = k1;
                perm[i2] = k2;
            } else {
                perm[i1] = k2;
                perm[i2] = k1;
            }
        }
    }
    printf("1");
    for (int i = 1; i <= n; ++i) {
        printf(" %d", perm[i]);
    }
    printf("\n");
    fflush(stdout);
    return 0;
}