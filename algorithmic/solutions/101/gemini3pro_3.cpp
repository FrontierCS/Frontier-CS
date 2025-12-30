#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <random>
#include <bitset>

using namespace std;

struct Node {
    int id;
    int u, v; // children indices
};

int N, R;
vector<Node> nodes;
vector<int> node_to_idx;
vector<vector<int>> levels;
vector<int> depth;
int max_depth = 0;

struct GateCoeffs {
    int CA; 
    int CB; 
};
vector<GateCoeffs> coeffs;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> R)) return 0;
    
    nodes.resize(N);
    node_to_idx.assign(2 * N + 1, -1);
    
    for (int i = 0; i < N; ++i) {
        cin >> nodes[i].u >> nodes[i].v;
        nodes[i].id = i;
        node_to_idx[i] = i;
    }

    depth.assign(2 * N + 1, -1);
    levels.clear();
    
    vector<int> q;
    q.push_back(0);
    depth[0] = 0;
    levels.resize(1);
    levels[0].push_back(0);
    
    int head = 0;
    while(head < q.size()){
        int u = q[head++];
        int children[2] = {nodes[u].u, nodes[u].v};
        for(int v : children){
            if(v < N){
                if(depth[v] == -1){
                    depth[v] = depth[u] + 1;
                    if(levels.size() <= depth[v]) levels.resize(depth[v] + 1);
                    levels[depth[v]].push_back(v);
                    q.push_back(v);
                }
            }
        }
    }
    max_depth = levels.size() - 1;

    coeffs.resize(N);
    vector<int> S(2 * N + 1, 0);
    mt19937 rng(1337);

    for (int d = 0; d <= max_depth; ++d) {
        vector<int>& layer = levels[d];
        if (layer.empty()) continue;

        int num_vars = 2 * layer.size() + 1;
        int num_queries = num_vars + 10;
        if (num_queries > 240) num_queries = 240; 
        
        vector<vector<int>> inputs(num_queries);
        vector<int> outputs(num_queries);
        
        for (int k = 0; k < num_queries; ++k) {
            vector<int> current_S = S;
            vector<int> perturbation(2 * layer.size());
            for (int i = 0; i < 2 * layer.size(); ++i) {
                perturbation[i] = rng() % 2;
            }
            
            for (int i = 0; i < layer.size(); ++i) {
                int u = layer[i];
                int left_child = nodes[u].u;
                int right_child = nodes[u].v;
                current_S[left_child] = (S[left_child] ^ perturbation[i]) & 1;
                current_S[right_child] = (S[right_child] ^ perturbation[layer.size() + i]) & 1;
            }
            
            inputs[k] = perturbation;
            
            cout << "? ";
            for (int j = 0; j <= 2 * N; ++j) cout << current_S[j];
            cout << endl;
            
            cin >> outputs[k];
        }
        
        vector<bitset<500>> mat(num_queries); 
        
        for (int k = 0; k < num_queries; ++k) {
            int rhs = outputs[k];
            for (int i = 0; i < layer.size(); ++i) {
                int dA = inputs[k][i];
                int dB = inputs[k][layer.size() + i];
                rhs ^= (dA & dB); 
                mat[k][i] = dA; 
                mat[k][layer.size() + i] = dB; 
            }
            mat[k][num_vars - 1] = 1; 
            mat[k][num_vars] = rhs; 
        }
        
        int pivot_row = 0;
        vector<int> solution(num_vars);
        vector<int> col_to_row(num_vars, -1);
        
        for (int col = 0; col < num_vars && pivot_row < num_queries; ++col) {
            int sel = -1;
            for (int row = pivot_row; row < num_queries; ++row) {
                if (mat[row][col]) {
                    sel = row;
                    break;
                }
            }
            if (sel == -1) continue;
            
            swap(mat[pivot_row], mat[sel]);
            col_to_row[col] = pivot_row;
            
            for (int row = 0; row < num_queries; ++row) {
                if (row != pivot_row && mat[row][col]) {
                    mat[row] ^= mat[pivot_row];
                }
            }
            pivot_row++;
        }
        
        for (int col = 0; col < num_vars; ++col) {
            if (col_to_row[col] != -1) {
                solution[col] = mat[col_to_row[col]][num_vars];
            } else {
                solution[col] = 0;
            }
        }
        
        for (int i = 0; i < layer.size(); ++i) {
            int u = layer[i];
            coeffs[u].CA = solution[i];
            coeffs[u].CB = solution[layer.size() + i];
            
            int left_child = nodes[u].u;
            int right_child = nodes[u].v;
            
            S[left_child] = 1 ^ coeffs[u].CB ^ S[left_child];
            S[right_child] = 1 ^ coeffs[u].CA ^ S[right_child];
        }
    }
    
    string result(N, ' ');
    vector<int> gate_out(N);

    for (int d = max_depth; d >= 0; --d) {
        for (int u : levels[d]) {
            int left = nodes[u].u;
            int right = nodes[u].v;
            
            int S_meas_L = 1 ^ coeffs[u].CB ^ S[left];
            int S_meas_R = 1 ^ coeffs[u].CA ^ S[right];
            
            int in_L, in_R;
            if (left >= N) in_L = S_meas_L;
            else in_L = gate_out[left] ^ S_meas_L;
            
            if (right >= N) in_R = S_meas_R;
            else in_R = gate_out[right] ^ S_meas_R;
            
            if (coeffs[u].CA == in_R) {
                result[u] = '&';
                int curr_in_L = (left >= N) ? S[left] : (gate_out[left] ^ S[left]);
                int curr_in_R = (right >= N) ? S[right] : (gate_out[right] ^ S[right]);
                gate_out[u] = curr_in_L & curr_in_R;
            } else {
                result[u] = '|';
                int curr_in_L = (left >= N) ? S[left] : (gate_out[left] ^ S[left]);
                int curr_in_R = (right >= N) ? S[right] : (gate_out[right] ^ S[right]);
                gate_out[u] = curr_in_L | curr_in_R;
            }
        }
    }

    cout << "! " << result << endl;

    return 0;
}