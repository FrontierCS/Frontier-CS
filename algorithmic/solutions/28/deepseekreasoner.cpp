#include <bits/stdc++.h>
using namespace std;

vector<string> query(const string& prefix, int K) {
    cout << "query " << prefix << " " << K << endl;
    cout.flush();
    int k;
    cin >> k;
    vector<string> res(k);
    for (int i = 0; i < k; ++i) {
        cin >> res[i];
    }
    return res;
}

void solve() {
    int N;
    cin >> N;
    set<string> all_words;
    for (char c = 'a'; c <= 'z'; ++c) {
        if ((int)all_words.size() >= N) break;
        string prefix(1, c);
        // initial probe with K=1
        vector<string> res = query(prefix, 1);
        for (const string& s : res) all_words.insert(s);
        if (res.empty()) continue; // no words with this prefix
        int K = 2;
        while (true) {
            if ((int)all_words.size() >= N) break;
            int k_val = min(K, N);
            res = query(prefix, k_val);
            for (const string& s : res) all_words.insert(s);
            if ((int)res.size() < k_val) break;
            if (k_val == N) break; // we have all words (all start with this prefix)
            K = min(K * 2, N);
        }
    }
    // output answer
    cout << "answer";
    for (const string& s : all_words) {
        cout << " " << s;
    }
    cout << endl;
    // no response expected
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