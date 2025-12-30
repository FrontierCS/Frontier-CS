#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    int L = 1, R = n;
    int questions_used = 0;
    int guesses_used = 0;

    auto ask_interval = [&](int l, int r) -> bool {
        int yes_cnt = 0, no_cnt = 0;
        for (int rep = 0; rep < 3 && questions_used < 53; ++rep) {
            int k = r - l + 1;
            cout << "? " << k;
            for (int i = l; i <= r; ++i) cout << " " << i;
            cout << "\n";
            cout.flush();
            string ans;
            if (!(cin >> ans)) exit(0);
            ++questions_used;
            if (ans == "YES") ++yes_cnt;
            else ++no_cnt;
        }
        return yes_cnt > no_cnt;
    };

    if (n == 1) {
        // Only possible value is 1
        cout << "! 1\n";
        cout.flush();
        string res;
        if (cin >> res) {}
        return 0;
    }

    while (L < R && questions_used + 3 <= 53) {
        int mid = (L + R) / 2;
        bool in_left = ask_interval(L, mid);
        if (in_left) R = mid;
        else L = mid + 1;
    }

    // Use guesses to finish
    while (guesses_used < 2 && L <= R) {
        int g = L;
        cout << "! " << g << "\n";
        cout.flush();
        ++guesses_used;
        string res;
        if (!(cin >> res)) return 0;
        if (res == ":)") return 0; // Correct guess, terminate

        // Wrong guess, remove g from consideration
        if (L == R) {
            // Only one candidate and it's wrong; choose any other valid number
            if (g > 1) --L;
            else if (g < n) ++L;
            else break;
            continue;
        }

        if (g == L) ++L;
        else if (g == R) --R;
        else {
            // Just move L past g
            L = g + 1;
        }
    }

    return 0;
}