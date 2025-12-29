#include <bits/stdc++.h>
using namespace std;

int main() {
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        int N;
        cin >> N;
        set<string> dictionary;
        for (char ch = 'a'; ch <= 'z'; ++ch) {
            if (dictionary.size() == static_cast<size_t>(N)) break;
            string pref(1, ch);
            int remaining = N - static_cast<int>(dictionary.size());
            vector<string> last_words;
            int bound = 1;
            bool done = false;
            while (!done) {
                int this_bound = min(bound, remaining);
                cout << "query " << pref << " " << this_bound << endl;
                cout.flush();
                int k;
                cin >> k;
                vector<string> curr(k);
                for (int j = 0; j < k; ++j) {
                    cin >> curr[j];
                }
                last_words = std::move(curr);
                if (k < this_bound) {
                    done = true;
                } else {
                    if (this_bound == remaining) {
                        done = true;
                    } else {
                        bound *= 2;
                    }
                }
            }
            for (const auto& w : last_words) {
                dictionary.insert(w);
            }
        }
        // Output answer
        cout << "answer";
        for (const auto& w : dictionary) {
            cout << " " << w;
        }
        cout << endl;
        cout.flush();
    }
    return 0;
}