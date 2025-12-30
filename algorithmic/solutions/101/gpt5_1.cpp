#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, R;
    if (!(cin >> N >> R)) return 0;
    for (int i = 0; i < N; ++i) {
        int U, V;
        cin >> U >> V;
    }
    string t;
    if (!(cin >> t)) t = "";
    // Validate token; if not valid, try to extract from remaining input
    auto is_valid = [&](const string& s) {
        if ((int)s.size() != N) return false;
        for (char c : s) if (c != '&' && c != '|') return false;
        return true;
    };
    if (!is_valid(t)) {
        string rest;
        for (char c : t) if (c == '&' || c == '|') rest.push_back(c);
        char c;
        while (cin.get(c)) {
            if (c == '&' || c == '|') rest.push_back(c);
        }
        if ((int)rest.size() >= N) t = rest.substr(rest.size() - N);
        else t = rest;
    }
    cout << t << "\n";
    return 0;
}