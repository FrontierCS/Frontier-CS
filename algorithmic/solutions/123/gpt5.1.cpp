#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int L = 1, R = n;
    int question_count = 0;
    int guess_count = 0;

    while (L < R && question_count < 53 && guess_count < 2) {
        int mid = (L + R) / 2;
        vector<int> S;
        for (int i = L; i <= mid; ++i) S.push_back(i);

        cout << "? " << S.size();
        for (int x : S) cout << ' ' << x;
        cout << '\n';
        cout.flush();

        string ans;
        if (!(cin >> ans)) return 0;
        ++question_count;

        if (ans == "YES") {
            R = mid;
        } else {
            L = mid + 1;
        }
    }

    cout << "! " << L << '\n';
    cout.flush();

    string res;
    cin >> res; // ":)" or ":("
    return 0;
}