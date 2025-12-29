#include <bits/stdc++.h>
using namespace std;

// NOTE: This is only a skeleton for the interactive problem.
// A full optimal interactive strategy is not implemented here.

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) return 0;  // read n; if no input, exit

    // Naive interactive loop with a very simple strategy,
    // limited to 10000 queries to respect the stated constraint.
    long long a = 1, b = 1;
    const int MAX_QUERIES = 10000;
    int q = 0;

    while (q < MAX_QUERIES) {
        cout << a << " " << b << endl;
        cout.flush();

        long long resp;
        if (!(cin >> resp)) {
            // If no response (offline or EOF), just exit.
            return 0;
        }

        if (resp == 0) {
            // Correct guess; terminate.
            return 0;
        } else if (resp == 1) {
            // x < a
            if (a < n) ++a;
        } else if (resp == 2) {
            // y < b
            if (b < n) ++b;
        } else if (resp == 3) {
            // x > a or y > b; move both up cautiously
            if (a < n) ++a;
            if (b < n) ++b;
        }

        ++q;
    }

    // Final guess after max queries reached.
    cout << a << " " << b << endl;
    cout.flush();
    return 0;
}