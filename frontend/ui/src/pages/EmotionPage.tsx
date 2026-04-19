import EmotionPanel from '../components/EmotionPanel';
import RelationshipPanel from '../components/RelationshipPanel';
import EmotionTimelinePanel from '../components/EmotionTimelinePanel';
import PersonalityFormPanel from '../components/PersonalityFormPanel';
import IdentityPanel from '../components/IdentityPanel';
import DataRing from '../components/DataRing';
import useMiyaQQData from '../hooks/useMiyaQQData';

const EmotionPage: React.FC = () => {
  const miyaData = useMiyaQQData();

  return (
    <div className="p-4 overflow-auto h-full space-y-4">
      <div className="text-cyan-400 text-sm font-medium">情感状态</div>
      
      <div className="grid grid-cols-3 gap-4">
        <div className="space-y-4">
          <IdentityPanel />
          <PersonalityFormPanel />
        </div>

        <div className="space-y-4">
          <EmotionPanel data={miyaData} />
          <RelationshipPanel relationship={miyaData.personality.relationship} />
        </div>

       <div className="space-y-4">
         <div className="grid grid-cols-2 gap-4">
           <EmotionTimelinePanel className="h-full" />
           
           <div className="glass-panel p-4 h-full">
             <div className="flex flex-col h-full gap-4">
               <div className="glass-panel p-4 h-[40%]">
                 <div className="text-cyan-400 text-xs mb-2">情感强度</div>
                 <DataRing 
                   value={miyaData.personality.emotion.intensity} 
                   label="强度" 
                   color="rgba(0, 188, 212, 0.3)"
                   size={120}
                 />
               </div>
               
               <div className="glass-panel p-4 h-[60%]">
                 <div className="text-cyan-400 text-xs mb-2">情感标签</div>
                 <div className="flex flex-wrap gap-2">
                   {miyaData.personality.emotion.emotion_tags.map((tag, i) => (
                     <span 
                       key={i}
                       className="px-3 py-1 rounded-full bg-gradient-to-r from-cyan-500/20 to-purple-500/20 text-cyan-400 text-xs"
                     >
                       {tag}
                     </span>
                   ))}
                 </div>
               </div>
             </div>
           </div>
         </div>
         
         <div className="glass-panel p-4">
           <div className="text-cyan-400 text-xs mb-2">内心独白</div>
           <div className="text-sm text-gray-300 italic">
             "{miyaData.personality.emotion.inner_thought}"
           </div>
         </div>
         
         <div className="glass-panel p-4">
           <div className="text-cyan-400 text-xs mb-2">情绪分析</div>
           <div className="text-xs text-gray-400 space-y-2">
             <p><span className="text-cyan-500">推理:</span> {miyaData.personality.emotion.reasoning}</p>
             <p><span className="text-purple-500">归因:</span> {miyaData.personality.emotion.attribution}</p>
             <p><span className="text-pink-500">反思:</span> {miyaData.personality.emotion.reflection}</p>
           </div>
         </div>
       </div>
      </div>
    </div>
  );
};

export default EmotionPage;