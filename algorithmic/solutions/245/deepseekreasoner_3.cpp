#include <bits/stdc++.h>
using namespace std;

int query(int i, int j) {
    printf("? %d %d\n", i, j);
    fflush(stdout);
    int ans;
    scanf("%d", &ans);
    if (ans == -1) exit(0); // invalid input, terminate
    return ans;
}

void answer(int x) {
    printf("! %d\n", x);
    fflush(stdout);
}

int main() {
    int t;
    scanf("%d", &t);
    while (t--) {
        int n;
        scanf("%d", &n);
        vector<int> good; // known non-impostors
        int cand = -1;    // current candidate (survivor)
        int a = -1, b = -1, ra = -1, rb = -1;
        bool broken = false;

        for (int i = 1; i <= n; ++i) {
            if (cand == -1) {
                cand = i;
            } else {
                int r1 = query(cand, i);
                int r2 = query(i, cand);
                if ((r1 == 0 && r2 == 0) || (r1 == 1 && r2 == 1)) {
                    // both are not impostor
                    good.push_back(cand);
                    good.push_back(i);
                    cand = -1;
                } else {
                    // one is impostor
                    a = cand;
                    b = i;
                    ra = r1;
                    rb = r2;
                    broken = true;
                    break;
                }
            }
        }

        if (!broken) {
            // only one candidate left
            answer(cand);
        } else {
            // need a third player c (non-impostor)
            int c;
            if (!good.empty()) {
                c = good[0];
            } else {
                c = 1;
                while (c == a || c == b) ++c;
            }
            int va = query(c, a);
            int vb = query(c, b);
            int diff = va ^ vb;
            int impostor;
            if (ra == 0) { // (0,1) case
                if (diff == 0) impostor = a;
                else impostor = b;
            } else { // (1,0) case
                if (diff == 0) impostor = b;
                else impostor = a;
            }
            answer(impostor);
        }
    }
    return 0;
}