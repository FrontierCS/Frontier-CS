#include <iostream>
#include <set>
#include <string>
#include <vector>

using namespace std;

int main() {
    int T;
    cin >> T;
    while (T--) {
        int N;
        cin >> N;
        set<string> words;
        
        for (char c = 'a'; c <= 'z'; ++c) {
            if (words.size() == N) break;
            string prefix(1, c);
            int K = 1;
            
            cout << "query " << prefix << " " << K << endl;
            cout.flush();
            
            int k;
            cin >> k;
            vector<string> res(k);
            for (int i = 0; i < k; ++i) cin >> res[i];
            for (const string& w : res) words.insert(w);
            
            if (words.size() == N) break;
            if (k == 0) continue;
            
            while (k == K) {
                if (K == N) break;
                K = min(K * 2, N);
                
                cout << "query " << prefix << " " << K << endl;
                cout.flush();
                
                cin >> k;
                res.resize(k);
                for (int i = 0; i < k; ++i) cin >> res[i];
                for (const string& w : res) words.insert(w);
                
                if (words.size() == N) break;
            }
            
            if (words.size() == N) break;
        }
        
        cout << "answer";
        for (const string& w : words) cout << " " << w;
        cout << endl;
        cout.flush();
    }
    
    return 0;
}