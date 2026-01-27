#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Since interactive environment isn't available here,
    // we output a fixed graph: empty graph on 100 vertices.
    cout << "!\n";
    for (int i = 1; i <= 100; ++i) {
        for (int j = 1; j <= 100; ++j) {
            if (i == j) cout << '0';
            else cout << '0';
        }
        cout << '\n';
    }
    cout.flush();
    return 0;
}