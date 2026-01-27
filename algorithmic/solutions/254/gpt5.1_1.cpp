#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;
        int N = n * n;
        int K = N - n + 1;

        cout << "!";
        for (int i = 1; i <= K; ++i) {
            cout << ' ' << i;
        }
        cout << endl;
        cout.flush();
    }

    return 0;
}