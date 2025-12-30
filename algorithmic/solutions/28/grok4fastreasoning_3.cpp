#include <bits/stdc++.h>
using namespace std;

int main() {
    int T;
    cin >> T;
    for (int t = 0; t < T; t++) {
        int N;
        cin >> N;
        set<string> all_words;
        vector<string> active;
        for (char ch = 'a'; ch <= 'z'; ch++) {
            string S(1, ch);
            cout << "query " << S << " 1" << endl;
            cout.flush();
            int k;
            cin >> k;
            for (int i = 0; i < k; i++) {
                string w;
                cin >> w;
                all_words.insert(w);
            }
            if (k == 1) {
                active.push_back(S);
            }
        }
        for (string S : active) {
            int cur = 1;
            while (true) {
                int nxt = cur * 2;
                if (nxt > N) nxt = N;
                cout << "query " << S << " " << nxt << endl;
                cout.flush();
                int kk;
                cin >> kk;
                for (int i = 0; i < kk; i++) {
                    string w;
                    cin >> w;
                    all_words.insert(w);
                }
                if (kk < nxt) break;
                cur = nxt;
                if (cur >= N) break;
            }
        }
        cout << "answer";
        for (const auto& w : all_words) {
            cout << " " << w;
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}