#include <iostream>
#include <string>
#include <vector>
#include <map>
#include <stack>
#include <cassert>

using namespace std;

struct Chamber {
    int id;
    int parent;           
    int entry_passage;    
    int next_passage;     
    int stone_side;       // 0 left, 1 right
    int stone_passage;    
    bool finished;
};

int m;
int next_id = 0;
vector<Chamber> chambers;
map<pair<int, int>, int> signature_to_id; // (side, passage) -> id
stack<int> dfs_stack;

void read_stone(string& side_str, int& passage) {
    cin >> side_str;
    if (side_str == "center") {
        passage = -1;
    } else if (side_str == "left" || side_str == "right") {
        cin >> passage;
    } else if (side_str == "treasure") {
        passage = -1;
    }
}

int side_to_int(const string& s) {
    if (s == "left") return 0;
    if (s == "right") return 1;
    return -1;
}

string int_to_side(int x) {
    return x == 0 ? "left" : "right";
}

int dist(int a, int b) {
    return (b - a + m) % m;
}

int main() {
    cin >> m;
    string side_str;
    int passage;

    read_stone(side_str, passage);
    assert(side_str == "center");

    Chamber root;
    root.id = next_id++;
    root.parent = -1;
    root.entry_passage = -1;
    root.next_passage = 0;
    root.stone_side = 0;
    root.stone_passage = 0;
    root.finished = false;
    chambers.push_back(root);
    signature_to_id[{0, 0}] = root.id;
    dfs_stack.push(root.id);

    cout << "0 left 0" << endl;

    while (true) {
        read_stone(side_str, passage);
        if (side_str == "treasure") {
            break;
        }

        int current_id;
        if (side_str == "center") {
            Chamber new_ch;
            new_ch.id = next_id++;
            new_ch.parent = dfs_stack.top();
            new_ch.entry_passage = -1;
            new_ch.next_passage = 0;
            new_ch.finished = false;

            int sig_side, sig_pass;
            if (new_ch.id < m) {
                sig_side = 0;
                sig_pass = new_ch.id;
            } else if (new_ch.id - m < m) {
                sig_side = 1;
                sig_pass = new_ch.id - m;
            } else {
                sig_side = (new_ch.id / m) % 2;
                sig_pass = new_ch.id % m;
            }
            new_ch.stone_side = sig_side;
            new_ch.stone_passage = sig_pass;
            chambers.push_back(new_ch);
            signature_to_id[{sig_side, sig_pass}] = new_ch.id;
            current_id = new_ch.id;
            dfs_stack.push(current_id);
        } else {
            int side_int = side_to_int(side_str);
            auto key = make_pair(side_int, passage);
            if (signature_to_id.find(key) == signature_to_id.end()) {
                Chamber new_ch;
                new_ch.id = next_id++;
                new_ch.parent = -1;
                new_ch.entry_passage = -1;
                new_ch.next_passage = 0;
                new_ch.stone_side = side_int;
                new_ch.stone_passage = passage;
                new_ch.finished = false;
                chambers.push_back(new_ch);
                signature_to_id[key] = new_ch.id;
                current_id = new_ch.id;
                dfs_stack.push(current_id);
            } else {
                current_id = signature_to_id[key];
            }
        }

        Chamber& cur = chambers[current_id];
        if (cur.next_passage < m) {
            int k = cur.next_passage;
            cur.next_passage++;
            int d1 = dist(cur.stone_passage, k);
            cout << d1 << " left " << d1 << endl;
            cur.stone_side = 0;
            cur.stone_passage = k;
            signature_to_id[{0, k}] = current_id;
        } else {
            cur.finished = true;
            if (cur.parent == -1) {
                int d1 = dist(cur.stone_passage, cur.stone_passage);
                cout << d1 << " right " << 0 << endl;
                cur.stone_side = 1;
                signature_to_id[{1, cur.stone_passage}] = current_id;
            } else {
                Chamber& par = chambers[cur.parent];
                int d1 = dist(cur.stone_passage, cur.entry_passage);
                int d2 = dist(cur.stone_passage, cur.entry_passage);
                cout << d1 << " right " << d2 << endl;
                cur.stone_side = 1;
                cur.stone_passage = cur.entry_passage;
                signature_to_id[{1, cur.entry_passage}] = current_id;
                dfs_stack.pop();
            }
        }
    }

    return 0;
}