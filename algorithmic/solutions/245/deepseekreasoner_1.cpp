#include <bits/stdc++.h>
using namespace std;

int ask(int i, int j) {
    cout << "? " << i << " " << j << endl;
    int ans;
    cin >> ans;
    if (ans == -1) exit(0);
    return ans;
}

void answer(int x) {
    cout << "! " << x << endl;
}

void solve() {
    int n;
    cin >> n;
    if (!cin) exit(0);
    
    int candidate = 1;
    for (int i = 2; i <= n; ++i) {
        int r1 = ask(candidate, i);
        int r2 = ask(i, candidate);
        if ((r1 == 1 && r2 == 0) || (r1 == 0 && r2 == 1)) {
            // impostor is either candidate or i
            int k = 1;
            while (k == candidate || k == i) ++k;
            int r3 = ask(k, candidate);
            int r4 = ask(k, i);
            int impostor;
            if (r1 == 1 && r2 == 0) {
                if (r3 == r4) impostor = i;
                else impostor = candidate;
            } else { // r1==0 && r2==1
                if (r3 == r4) impostor = candidate;
                else impostor = i;
            }
            answer(impostor);
            return;
        }
        // else: (1,1) or (0,0) => candidate stays, continue
    }
    // Should never reach here because impostor must cause (1,0) or (0,1)
    // But just in case, guess candidate (won't happen with correct logic)
    answer(candidate);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}