#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

using namespace std;

struct Instruction {
    string type; // "POP" or "HALT"
    int a; // used for POP check or ignored
    int x; // GOTO x
    int b; // PUSH b
    int y; // GOTO y
};

struct Layer {
    int id_E;
    int id_M;
    int id_D_Main;
    int id_D_Gate;
    int id_D_Check2;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    long long k;
    if (!(cin >> k)) return 0;

    if (k == 1) {
        cout << "1\nHALT PUSH 1 GOTO 1\n";
        return 0;
    }

    long long T = k - 3;
    vector<char> types; 
    
    while (T > 0) {
        if (T >= 6 && (T - 6) % 4 == 0) { 
            types.push_back('A');
            T = (T - 6) / 2;
        } else {
            types.push_back('B');
            T = T - 2;
        }
    }
    
    // types correspond to building layer j+1 from j.
    // We reverse so index j corresponds to Layer j+1.
    reverse(types.begin(), types.end());
    
    int num_layers = types.size() + 1; 
    vector<Layer> layers(num_layers);
    
    int current_id = 2; // ID 1 is HALT
    
    // Allocate IDs
    for (int i = 0; i < num_layers; ++i) {
        // Body
        if (i > 0) {
            char type = types[i-1];
            layers[i].id_E = current_id++;
            if (type == 'A') {
                layers[i].id_M = current_id++;
            }
        }
        
        // Dispatcher
        int parent_idx = i + 1;
        char parent_type = (parent_idx >= num_layers) ? 'R' : types[parent_idx-1];
        
        layers[i].id_D_Main = current_id++;
        if (parent_type == 'A') {
            layers[i].id_D_Gate = current_id++;
            layers[i].id_D_Check2 = current_id++;
        }
    }
    
    vector<Instruction> code(current_id); 
    int V_counter = 1;
    int V_root = V_counter++;
    int Dummy = 1000;
    
    // Precompute Values per layer
    vector<pair<int,int>> layer_values(num_layers); 
    for(int i=1; i<num_layers; ++i) {
        char t = types[i-1];
        layer_values[i].first = V_counter++;
        if(t == 'A') layer_values[i].second = V_counter++;
    }
    
    // Generate Code
    for(int i=0; i<num_layers; ++i) {
        // 1. Dispatcher of Layer i (Handles returns to Parent i+1)
        int parent = i + 1;
        int V1, V2;
        int target1, target2;
        
        if (parent == num_layers) { // Root
            V1 = V_root;
            target1 = 1;
            code[layers[i].id_D_Main] = {"POP", V1, target1, 1, 1};
        } else {
            char p_type = types[i]; // Type of Layer i+1
            V1 = layer_values[parent].first;
            V2 = layer_values[parent].second;
            
            if (p_type == 'A') {
                target1 = layers[parent].id_M;
                target2 = layers[parent].id_D_Main;
                
                code[layers[i].id_D_Main] = {"POP", V1, target1, V1, layers[i].id_D_Gate};
                code[layers[i].id_D_Gate] = {"POP", V1, layers[i].id_D_Check2, 1, 1};
                code[layers[i].id_D_Check2] = {"POP", V2, target2, 1, 1};
            } else { // B
                target1 = layers[parent].id_D_Main;
                code[layers[i].id_D_Main] = {"POP", V1, target1, 1, 1};
            }
        }
        
        // 2. Body of Layer i (Calls Child i-1)
        if (i > 0) {
            char my_type = types[i-1];
            int child_entry = (i-1 == 0) ? layers[i-1].id_D_Main : layers[i-1].id_E;
            int my_v1 = layer_values[i].first;
            int my_v2 = layer_values[i].second;
            
            if (my_type == 'A') {
                code[layers[i].id_E] = {"POP", Dummy, 1, my_v1, child_entry};
                code[layers[i].id_M] = {"POP", Dummy, 1, my_v2, child_entry};
            } else {
                code[layers[i].id_E] = {"POP", Dummy, 1, my_v1, child_entry};
            }
        }
    }
    
    // Node 1
    int top_entry = (num_layers == 1) ? layers[0].id_D_Main : layers[num_layers-1].id_E;
    code[1] = {"HALT", 0, 0, V_root, top_entry};
    
    // Output
    cout << current_id - 1 << endl;
    for (int i = 1; i < current_id; ++i) {
        if (code[i].type == "HALT") {
            cout << "HALT PUSH " << code[i].b << " GOTO " << code[i].y << endl;
        } else {
            cout << "POP " << code[i].a << " GOTO " << code[i].x << " PUSH " << code[i].b << " GOTO " << code[i].y << endl;
        }
    }

    return 0;
}