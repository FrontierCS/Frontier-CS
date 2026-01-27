#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;

    // Dummy strategy: output N pairs (i, i+N)
    // This is not a correct interactive solution; it's a placeholder.
    for (int i = 1; i <= N; ++i) {
        cout << "Answer " << i << " " << (i + N) << "\n";
        cout.flush();
    }
    return 0;
}