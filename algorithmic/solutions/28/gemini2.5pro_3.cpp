#include <iostream>
#include <vector>
#include <string>
#include <set>
#include <queue>
#include <map>
#include <algorithm>

using namespace std;

// Function to send a query and parse the response
vector<string> do_query(const string& s, int k) {
    cout << "query " << s << " " << k << endl;
    int count;
    cin >> count;
    vector<string> words(count);
    for (int i = 0; i < count; ++i) {
        cin >> words[i];
    }
    return words;
}

void solve() {
    int n;
    cin >> n;

    set<string> found_words;
    queue<string> q;
    set<string> q_set;

    for (char c = 'a'; c <= 'z'; ++c) {
        string s(1, c);
        q.push(s);
        q_set.insert(s);
    }

    while (found_words.size() < n && !q.empty()) {
        string s = q.front();
        q.pop();

        vector<string> words_s;
        int k = 1;

        while (true) {
            if (found_words.size() == n) break;
            
            vector<string> current_words = do_query(s, k);
            
            for (const auto& word : current_words) {
                found_words.insert(word);
            }

            words_s = current_words;

            if (current_words.size() < k) {
                break;
            }
            
            if (k >= n) {
                break;
            }
            
            k *= 2;
            if (k > n) {
                k = n;
            }
        }

        if (s.length() < 10) {
            map<char, vector<string>> groups;
            for (const auto& word : words_s) {
                if (word.length() > s.length()) {
                    groups[word[s.length()]].push_back(word);
                }
            }

            for (auto const& [key, val] : groups) {
                string next_s = s + key;
                
                bool next_s_is_word = false;
                for(const auto& w : val) {
                    if (w == next_s) {
                        next_s_is_word = true;
                        break;
                    }
                }

                if (val.size() > 1 || (val.size() == 1 && !next_s_is_word)) {
                    if (q_set.find(next_s) == q_set.end()) {
                        q.push(next_s);
                        q_set.insert(next_s);
                    }
                }
            }
        }
    }

    cout << "answer";
    for (const auto& word : found_words) {
        cout << " " << word;
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout.flush();
    int t;
    cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}