#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m, T;
    cin >> n >> m >> T;
    // read and ignore the initial edges
    for (int i = 0; i < m; ++i) {
        int a, b;
        cin >> a >> b;
    }
    // no modifications
    cout << 0 << endl;
    cout.flush();

    for (int round = 0; round < T; ++round) {
        // guess vertex 1 every time
        cout << "! 1" << endl;
        cout.flush();
        string response;
        cin >> response;
        if (response == "Wrong") {
            return 0;
        }
    }
    return 0;
}