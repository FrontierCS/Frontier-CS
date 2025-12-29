#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n == 1) {
        cout << "1 1\n";
        cout.flush();
        return 0;
    }

    vector<int> q(n + 1);

    auto ask = [&](const vector<int>& arr) -> int {
        cout << 0;
        for (int i = 1; i <= n; ++i) {
            cout << ' ' << arr[i];
        }
        cout << '\n';
        cout.flush();
        int x;
        if (!(cin >> x)) exit(0);
        return x;
    };

    // Step 0: find positions of values 1 and 2
    vector<int> fi(n + 1);
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) q[j] = 2;
        q[i] = 1;
        fi[i] = ask(q);
    }

    int pos1 = 1, pos2 = 1;
    for (int i = 2; i <= n; ++i) {
        if (fi[i] > fi[pos1]) pos1 = i;
        if (fi[i] < fi[pos2]) pos2 = i;
    }

    vector<int> posOfVal(n + 1);
    posOfVal[1] = pos1;
    posOfVal[2] = pos2;

    auto inRange = [&](int v, int L, int R) -> bool {
        for (int i = 1; i <= n; ++i) {
            if (i >= L && i <= R) q[i] = v;
            else q[i] = 1;
        }
        int fA = ask(q);
        int D = fA - 1; // all-ones query has exactly one match (value 1)
        bool b1 = (pos1 >= L && pos1 <= R);
        int val = D + (b1 ? 1 : 0);
        return val == 1;
    };

    // Find positions for values 3..n via binary search
    for (int v = 3; v <= n; ++v) {
        int L = 1, R = n;
        while (L < R) {
            int mid = (L + R) / 2;
            if (inRange(v, L, mid)) R = mid;
            else L = mid + 1;
        }
        posOfVal[v] = L;
    }

    vector<int> ans(n + 1);
    for (int v = 1; v <= n; ++v) {
        ans[posOfVal[v]] = v;
    }

    cout << 1;
    for (int i = 1; i <= n; ++i) {
        cout << ' ' << ans[i];
    }
    cout << '\n';
    cout.flush();

    return 0;
}