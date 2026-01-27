#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long n;
    if (!(cin >> n)) {
        cout << "! 0" << endl;
        return 0;
    }

    // Output any arbitrary index as per the note.
    long long idx = 0;
    if (n > 0) {
        idx = 0;
    }
    cout << "! " << idx << endl;
    return 0;
}