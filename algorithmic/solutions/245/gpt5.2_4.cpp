#include <bits/stdc++.h>
using namespace std;

static int ask(int i, int j) {
    cout << "? " << i << " " << j << '\n';
    cout.flush();
    int r;
    if (!(cin >> r)) exit(0);
    if (r == -1) exit(0);
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;

        pair<int,int> suspect = {-1, -1};
        int witness = -1;
        int leftover = -1;

        for (int i = 1; i <= n; i += 2) {
            if (i == n) {
                leftover = i;
                break;
            }
            int a = ask(i, i + 1);
            int b = ask(i + 1, i);
            if (a == b) {
                if (witness == -1) witness = i;
            } else {
                suspect = {i, i + 1};
            }
        }

        int ans = -1;
        if (suspect.first == -1) {
            ans = leftover;
        } else {
            if (witness == -1) witness = leftover; // leftover exists only if n is odd; then it's surely non-impostor
            int a = suspect.first, b = suspect.second, k = witness;
            int x = ask(k, a);
            int y = ask(a, k);
            ans = (x != y) ? a : b;
        }

        cout << "! " << ans << '\n';
        cout.flush();
    }
    return 0;
}