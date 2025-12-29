#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <algorithm>

using namespace std;

map<string, vector<string>> cache;

vector<string> query(const string& S, int K) {
    if (cache.count(S) && (int)cache[S].size() >= K) {
        return vector<string>(cache[S].begin(), cache[S].begin() + K);
    }
    cout << "query " << S << " " << K << endl;
    cout.flush();
    int k;
    cin >> k;
    vector<string> res(k);
    for (int i = 0; i < k; ++i) {
        cin >> res[i];
    }
    cache[S] = res;
    return res;
}

string find_successor(const string& w) {
    int n = w.size();
    for (int i = n; i >= 0; --i) {
        string prefix = w.substr(0, i);
        if (i == n) {
            if (n < 10) {
                vector<string> res = query(w, 2);
                if ((int)res.size() >= 2) {
                    return res[1];
                }
            }
        } else {
            char start_char = w[i];
            for (char c = start_char + 1; c <= 'z'; ++c) {
                string candidate = prefix + c;
                vector<string> res = query(candidate, 1);
                if (!res.empty()) {
                    return res[0];
                }
            }
        }
    }
    return "";
}

void solve() {
    cache.clear();
    int N;
    cin >> N;
    vector<string> words;
    // find smallest word
    string first_word = "";
    for (char c = 'a'; c <= 'z'; ++c) {
        string pref(1, c);
        vector<string> res = query(pref, 1);
        if (!res.empty()) {
            first_word = res[0];
            break;
        }
    }
    words.push_back(first_word);
    while ((int)words.size() < N) {
        string nxt = find_successor(words.back());
        // nxt must exist because we haven't found all words yet
        words.push_back(nxt);
    }
    cout << "answer";
    for (const string& s : words) {
        cout << " " << s;
    }
    cout << endl;
    cout.flush();
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    cin >> T;
    while (T--) {
        solve();
    }
    return 0;
}