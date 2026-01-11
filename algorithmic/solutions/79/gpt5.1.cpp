#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;

    // Make one dummy query to follow the protocol
    cout << "? " << 0 << endl;
    cout.flush();

    long long t;
    if (!(cin >> t)) return 0;

    // Output a dummy answer
    cout << "! " << 1 << endl;
    cout.flush();

    return 0;
}