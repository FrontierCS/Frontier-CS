#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, R;
    while (cin >> N >> R) {
        for (int i = 0; i < N; ++i) {
            int U, V;
            if (!(cin >> U >> V)) return 0;
        }
        string t;
        char ch;
        // Read exactly N characters of '&' or '|' ignoring whitespace
        while ((int)t.size() < N && cin.get(ch)) {
            if (ch == '&' || ch == '|') t.push_back(ch);
        }
        if ((int)t.size() != N) break;
        cout << t << "\n";
    }
    return 0;
}