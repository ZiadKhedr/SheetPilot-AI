import * as Dialog from '@radix-ui/react-dialog';
import { X, LoaderCircle } from 'lucide-react';
import type { ReactNode } from 'react';
export function Button({children,onClick,disabled=false,variant='',type='button',className='',...rest}:{children:ReactNode;onClick?:()=>void;disabled?:boolean;variant?:string;type?:'button'|'submit';className?:string;[key:string]:unknown}){
 return <button {...rest} type={type} className={'button '+variant+' '+className} disabled={disabled} onClick={onClick}>{children}</button>
}
export function Badge({children,tone=''}:{children:ReactNode;tone?:string}){return <span className={'badge '+tone}>{children}</span>}
export function Modal({open,onOpenChange,title,description,children}:{open:boolean;onOpenChange:(v:boolean)=>void;title:string;description:string;children:ReactNode}){
 return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="modal-overlay"/><Dialog.Content className="modal"><Dialog.Title className="modal-title">{title}</Dialog.Title><Dialog.Description className="subtle">{description}</Dialog.Description><Dialog.Close className="icon-button modal-close" aria-label="Close dialog"><X size={19}/></Dialog.Close>{children}</Dialog.Content></Dialog.Portal></Dialog.Root>
}
export function Busy({message='Working…'}:{message?:string}){return <span className="busy" role="status"><LoaderCircle size={16} className="spin"/>{message}</span>}
export function Empty({icon,title,children}:{icon:ReactNode;title:string;children:ReactNode}){return <div className="empty"><div className="empty-icon">{icon}</div><h3>{title}</h3><p>{children}</p></div>}
export function SectionTitle({eyebrow,title,description,action}:{eyebrow?:string;title:string;description?:string;action?:ReactNode}){return <div className="section-title"><div>{eyebrow&&<div className="eyebrow">{eyebrow}</div>}<h2>{title}</h2>{description&&<p>{description}</p>}</div>{action}</div>}
