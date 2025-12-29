#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int diamond = 0;  // fallback in case we never see (0,0)

    for (int i = 0; i < n; ++i) {
        cout << "? " << i << endl;
        cout.flush();

        long long a0, a1;
        if (!(cin >> a0 >> a1)) return 0;

        if (a0 == 0 && a1 == 0) {
            diamond = i;
            break;
        }
    }

    cout << "! " << diamond << endl;
    cout.flush();
    return 0;
}