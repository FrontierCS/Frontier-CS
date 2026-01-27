#include <bits/stdc++.h>
using namespace std;

bool isNumber(const string& s) {
    if (s.empty()) return false;
    for (char c : s) if (!isdigit((unsigned char)c)) return false;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    for (int tc = 0; tc < T; ++tc) {
        int N;
        if (!(cin >> N)) return 0;
        unordered_set<string> st;
        st.reserve(N * 2 + 5);
        vector<string> words;
        words.reserve(N);
        
        while ((int)st.size() < N) {
            string tok;
            if (!(cin >> tok)) break;
            if (isNumber(tok)) {
                int k = stoi(tok);
                for (int i = 0; i < k; ++i) {
                    string w; 
                    cin >> w;
                    if (st.insert(w).second) {
                        words.push_back(w);
                    }
                }
            } else {
                // Direct word
                if (st.insert(tok).second) {
                    words.push_back(tok);
                }
            }
        }
        // Ensure exactly N words (in case of duplicates or extra tokens)
        if ((int)words.size() > N) {
            // Remove extras by preserving first occurrence order
            unordered_set<string> seen;
            seen.reserve(N * 2 + 5);
            vector<string> trimmed;
            trimmed.reserve(N);
            for (const string& w : words) {
                if ((int)trimmed.size() == N) break;
                if (seen.insert(w).second) trimmed.push_back(w);
            }
            words.swap(trimmed);
        } else if ((int)words.size() < N) {
            // In rare malformed inputs, try to read more tokens as words
            while ((int)words.size() < N) {
                string w;
                if (!(cin >> w)) break;
                if (isNumber(w)) {
                    int k = stoi(w);
                    for (int i = 0; i < k; ++i) {
                        string ww; 
                        cin >> ww;
                        if (st.insert(ww).second) words.push_back(ww);
                        if ((int)words.size() == N) break;
                    }
                } else {
                    if (st.insert(w).second) words.push_back(w);
                }
            }
        }
        
        cout << "answer";
        for (int i = 0; i < N && i < (int)words.size(); ++i) {
            cout << ' ' << words[i];
        }
        cout << '\n';
    }
    return 0;
}