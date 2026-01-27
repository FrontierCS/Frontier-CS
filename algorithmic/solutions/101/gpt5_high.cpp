#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<string> answers;
    while (true) {
        int N, R;
        if (!(cin >> N >> R)) break;
        for (int i = 0; i < N; ++i) {
            int U, V;
            cin >> U >> V;
        }
        // Attempt to read the gate string if present
        // Skip whitespace
        while (cin && isspace(cin.peek())) cin.get();
        if (!cin) break;
        char c = cin.peek();
        if (c == '&' || c == '|') {
            string t;
            cin >> t;
            answers.push_back(t);
        } else {
            // If no gate string follows, we cannot proceed meaningfully; break
            break;
        }
    }
    
    for (size_t i = 0; i < answers.size(); ++i) {
        if (i) cout << '\n';
        cout << answers[i];
    }
    return 0;
}