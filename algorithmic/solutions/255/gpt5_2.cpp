#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) break;
        vector<int> v;
        v.reserve(n);
        string tok;
        while ((int)v.size() < n && (cin >> tok)) {
            bool isLetters = true;
            for (char c : tok) {
                if (c != 'N' && c != 'S' && c != '-') { isLetters = false; break; }
            }
            if (isLetters) {
                for (char c : tok) {
                    if ((int)v.size() >= n) break;
                    if (c == 'N') v.push_back(1);
                    else if (c == 'S') v.push_back(-1);
                    else v.push_back(0);
                }
            } else {
                // Try to parse as integer tokens -1, 0, 1
                if (tok == "-1") v.push_back(-1);
                else if (tok == "0") v.push_back(0);
                else if (tok == "1") v.push_back(1);
                else if (tok.size() == 1) {
                    char c = tok[0];
                    if (c == 'N') v.push_back(1);
                    else if (c == 'S') v.push_back(-1);
                    else if (c == '-') v.push_back(0);
                    else {
                        // Fallback: try general integer parsing
                        try {
                            int x = stoi(tok);
                            v.push_back(x);
                        } catch (...) {
                            // Unknown token, assume 0
                            v.push_back(0);
                        }
                    }
                } else {
                    // Fallback: try general integer parsing
                    try {
                        int x = stoi(tok);
                        v.push_back(x);
                    } catch (...) {
                        // If token contains only N/S/- sequence but length > remaining, take as many as needed
                        bool letters = true;
                        for (char c : tok) {
                            if (c != 'N' && c != 'S' && c != '-') { letters = false; break; }
                        }
                        if (letters) {
                            for (char c : tok) {
                                if ((int)v.size() >= n) break;
                                if (c == 'N') v.push_back(1);
                                else if (c == 'S') v.push_back(-1);
                                else v.push_back(0);
                            }
                        } else {
                            // Unknown token, fill remaining with zeros (best effort)
                            while ((int)v.size() < n) v.push_back(0);
                        }
                    }
                }
            }
        }
        vector<int> zeros;
        for (int i = 0; i < n; ++i) if (v[i] == 0) zeros.push_back(i + 1);
        cout << zeros.size();
        for (int x : zeros) cout << ' ' << x;
        cout << '\n';
    }
    return 0;
}