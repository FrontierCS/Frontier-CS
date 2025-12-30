#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<int> op(n + 1, -1); // 0 for '+', 1 for '*'
    vector<int> a(n + 1);

    for (int i = n; i >= 1; --i) {
        a[0] = 0;
        for (int j = 1; j < i; ++j) a[j] = 0;
        a[i] = 1;
        for (int j = i + 1; j <= n; ++j) {
            if (op[j] == 0) a[j] = 0; // neutral for addition
            else a[j] = 1;            // neutral for multiplication
        }

        cout << "?";
        for (int j = 0; j <= n; ++j) cout << " " << a[j];
        cout << endl;
        cout.flush();

        int res;
        cin >> res;
        op[i] = (res == 1 ? 0 : 1);
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) cout << " " << op[i];
    cout << endl;
    cout.flush();

    return 0;
}