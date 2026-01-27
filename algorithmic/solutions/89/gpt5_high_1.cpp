#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    auto ask = [&](int v, int a, int b)->int {
        cout << "? 2 " << v << " " << a << " " << b << "\n";
        cout.flush();
        int ans;
        if (!(cin >> ans)) exit(0);
        if (ans == -1) exit(0);
        return ans;
    };

    int r = 1;
    vector<int> parent(n + 1, -1);
    parent[r] = 0;

    for (int x = 1; x <= n; ++x) {
        if (x == r) continue;
        int p = r; // candidate on path r-x
        for (int y = 1; y <= n; ++y) {
            if (y == x || y == r) continue;
            int on = ask(y, r, x);
            if (on == 1) {
                int comp = ask(p, r, y);
                if (comp == 1) p = y;
            }
        }
        parent[x] = p;
    }

    cout << "!\n";
    for (int i = 1; i <= n; ++i) {
        if (i == r) continue;
        cout << parent[i] << " " << i << "\n";
    }
    cout.flush();
    return 0;
}