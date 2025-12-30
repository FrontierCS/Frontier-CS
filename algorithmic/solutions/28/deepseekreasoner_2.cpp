#include <iostream>
#include <vector>
#include <string>

using namespace std;

vector<string> query(const string& prefix, int K) {
    cout << "query " << prefix << " " << K << endl;
    int k;
    cin >> k;
    vector<string> res(k);
    for (int i = 0; i < k; ++i) {
        cin >> res[i];
    }
    return res;
}

void answer(const vector<string>& words) {
    cout << "answer";
    for (const string& w : words) {
        cout << " " << w;
    }
    cout << endl;
}

int main() {
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        int N;
        cin >> N;
        vector<string> all_words;
        int found = 0;
        for (char c = 'a'; c <= 'z'; ++c) {
            if (found >= N) break;
            string prefix(1, c);
            auto words = query(prefix, 1);
            int current_k = 1;
            int k = words.size();
            if (k == 0) continue;
            while (true) {
                if (k < current_k) break;
                // k == current_k
                int next_k = current_k * 2;
                if (next_k > N + 1) next_k = N + 1;
                if (next_k == current_k) break; // safety
                auto new_words = query(prefix, next_k);
                int new_k = new_words.size();
                words = new_words;
                current_k = next_k;
                k = new_k;
                if (k < current_k) break;
            }
            found += words.size();
            all_words.insert(all_words.end(), words.begin(), words.end());
        }
        answer(all_words);
    }
    return 0;
}