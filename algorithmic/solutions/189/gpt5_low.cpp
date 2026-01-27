#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    string s1, s2;
    if (!getline(cin, s1)) return 0;
    if (!getline(cin, s2)) return 0;

    size_t n = s1.size(), m = s2.size();
    size_t i = 0, j = 0;

    string out;
    out.reserve(n + m);

    const int W = 12;

    while (i < n && j < m) {
        if (s1[i] == s2[j]) {
            out.push_back('M');
            ++i; ++j;
            continue;
        }

        int a = -1, b = -1;

        // Lookahead for insertion (advance in s2)
        for (int k = 1; k <= W; ++k) {
            if (j + k >= m) break;
            if (s1[i] == s2[j + k]) { a = k; break; }
        }
        // Lookahead for deletion (advance in s1)
        for (int k = 1; k <= W; ++k) {
            if (i + k >= n) break;
            if (s1[i + k] == s2[j]) { b = k; break; }
        }

        if (a == -1 && b == -1) {
            // Substitute
            out.push_back('M');
            ++i; ++j;
        } else if (a != -1 && (b == -1 || a <= b)) {
            // Insert a characters from s2
            out.append(a, 'I');
            j += a;
        } else {
            // Delete b characters from s1
            out.append(b, 'D');
            i += b;
        }
    }

    if (i < n) out.append(n - i, 'D');
    if (j < m) out.append(m - j, 'I');

    cout << out << '\n';
    return 0;
}