#include <bits/stdc++.h>
using namespace std;

int main() {
    int T;
    cin >> T;
    for (int t = 0; t < T; t++) {
        int N;
        cin >> N;
        vector<string> all_words;
        for (char ch = 'a'; ch <= 'z'; ch++) {
            string prefix = "";
            prefix += ch;
            vector<string> group;
            int cur_k = 1;
            while (true) {
                int query_k = min(cur_k, N);
                cout << "query " << prefix << " " << query_k << endl;
                cout.flush();
                int kk;
                cin >> kk;
                vector<string> temp(kk);
                for (int i = 0; i < kk; i++) {
                    cin >> temp[i];
                }
                bool complete = (kk < query_k) || (query_k == N && kk == query_k);
                if (complete) {
                    group = temp;
                    break;
                }
                cur_k = min(N, cur_k * 2);
            }
            for (auto &w : group) {
                all_words.push_back(w);
            }
        }
        cout << "answer";
        for (auto &w : all_words) {
            cout << " " << w;
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}